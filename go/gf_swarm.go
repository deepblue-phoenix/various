//README - utility functions for working with Docker swarm

package gf_core

import (
	"fmt"
	"time"
	"strconv"
	"strings"
	"gopkg.in/mgo.v2"
)
//-------------------------------------------------
func Swarm__create_cluster(p_ssh__user_str *string,
					p_ssh__host_str *string,
					p_log_fun       func(string,string)) (*string,error) {
	p_log_fun("FUN_ENTER","gf_swarm.Swarm__create_cluster()")
	
	//"--rm" - remove command container after running it
	c     := "docker run --rm swarm create"
	r,err := Ssh_run_cmd(c,p_ssh__user_str,p_ssh__host_str,p_log_fun)

	if err != nil {
		return nil,err
	}

	cluster_id_str := r
	return cluster_id_str,nil
}
//-------------------------------------------------
func Swarm__db_create_cluster_info(p_cluster_name_str *string,
							p_swarm_cluster_id_str *string,
							p_mongo_db             *mgo.Database,
							p_log_fun              func(string,string)) error {
	p_log_fun("FUN_ENTER","gf_swarm.Swarm__db_create_cluster_info()")

	coll                   := p_mongo_db.C("swarm_cluster_info")
	creation_unix_time_str := strconv.FormatFloat(float64(time.Now().UnixNano())/1000000000.0,'f',10,64)
	
	swarm__cluster_info_map := map[string]string{
			"obj_class_str"         :"gf_swarm_cluster_info",
			"creation_unix_time_str":creation_unix_time_str,
			"name_str"              :*p_cluster_name_str,
			"swarm_cluster_id_str"  :*p_swarm_cluster_id_str,
		}

	err := coll.Insert(&swarm__cluster_info_map)
	if err != nil {
		return err
	}
	return nil
}
//-------------------------------------------------
func Swarm__db_get_cluster_info(p_mongodb_coll *mgo.Collection,
						p_log_fun func(string,string)) (map[string]interface{},error) {
	return nil,nil
}
//-------------------------------------------------
func Swarm__init_manager(p_swarm_cluster_id_str *string,
					p_swarm_manager_port_str *string,
					p_ssh__user_str          *string,
					p_ssh__host_str          *string,
					p_log_fun                func(string,string)) {
	p_log_fun("FUN_ENTER","gf_swarm.Swarm__init_manager()")

	//pull swarm image so its present
	Ssh_run_cmd("docker pull swarm",p_ssh__user_str,p_ssh__host_str,p_log_fun)

	//---------------------------------------------------
	//make swarm_manager start on system boot

	init_startup__on_boot := func(p_deamon__cmd_str string) {
		p_log_fun("FUN_ENTER","gf_swarm.Swarm__init_manager().init_startup__on_boot()")

		os_startup_script_path_str := "/etc/rc.local"
		//----------------
		//cleanup

		//'exit 0' - anything after this line is not exectuced, so comment it out.
		//           this is present in rc.local by default, or from previous runs of this or other scripts
		Ssh__comment_line_in_file(&os_startup_script_path_str,
							"exit 0",         //p_target__line_start_str
							p_ssh__user_str,
							p_ssh__host_str,
							p_log_fun)

		//comment out if any previous docker startup commands exist, written by other programs,
		//or previous runs of this program
		Ssh__comment_line_in_file(&os_startup_script_path_str,
							"^docker run -p ",
							p_ssh__user_str,
							p_ssh__host_str,
							p_log_fun)
		//----------------
		//add config
		ssh__append_line_to_file(&os_startup_script_path_str,p_deamon__cmd_str,p_ssh__user_str,p_ssh__host_str,p_log_fun)
		ssh__append_line_to_file(&os_startup_script_path_str,"exit 0"         ,p_ssh__user_str,p_ssh__host_str,p_log_fun)
	}
	//---------------------------------------------------

	//START MANAGER - to which the docker client will connect to, to issue docker commands
	c_lst := []string{
		"docker",
		"run",
		"--rm", //remove container after done running
		fmt.Sprintf("-p %s:%s",*p_swarm_manager_port_str,*p_swarm_manager_port_str),
		"swarm",
		"manage",

		//IMPORTANT!! - host/port on which this manger is going to listen
		fmt.Sprintf("--host=0.0.0.0:%s",*p_swarm_manager_port_str),

		"token://"+*p_swarm_cluster_id_str,
	}

	c_str := strings.Join(c_lst," ")
	init_startup__on_boot(c_str)

	//--------------------
	//START MANAGER ON MASTER

	Ssh_run_cmd("apt-get install dtach",p_ssh__user_str,p_ssh__host_str,p_log_fun) //REMOVE!! - dont 'apt-get install' do it every time here
	Ssh_run_cmd(fmt.Sprintf("dtach -n `mktemp -u /tmp/dtach.XXXX` %s",c_str),p_ssh__user_str,p_ssh__host_str,p_log_fun)
	//--------------------
}
//-------------------------------------------------
func Swarm__join_node_to_cluster(p_cluster_id_str *string,
					p_member_host_str                      *string,
					p_docker_port_str                      *string,
					p_docker_kv_store__etcd__host_port_str *string,
					p_ssh__host_str                        *string,
					p_ssh__user_str                        *string,
					p_log_fun                              func(string,string)) {
	p_log_fun("FUN_ENTER","gf_swarm.Swarm__join_node_to_cluster()")

	c_lst := []string{
		"docker",
		"run",
		"-d",   //run detached
		"--rm", //remove container after done running
		"swarm",
		"join",
		"token://"+*p_cluster_id_str,
		fmt.Sprintf("--addr=%s:%s",*p_member_host_str,*p_docker_port_str),
		"etcd://"+*p_docker_kv_store__etcd__host_port_str,
	}

	cmd_str := strings.Join(c_lst,"")
	p_log_fun("INFO",fmt.Sprintf("++++++++++  MEMBER JOIN SWARM - Docker Host %s:%s",*p_member_host_str,
																				*p_docker_port_str))
	p_log_fun("INFO",cmd_str)

	Ssh_run_cmd(cmd_str,p_ssh__user_str,p_ssh__host_str,p_log_fun)
}