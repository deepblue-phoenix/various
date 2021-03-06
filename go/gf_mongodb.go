//README - utility functions for working with mongodb

package gf_core

import (
	"encoding/json"
	"fmt"
	"gopkg.in/mgo.v2"
	"os"
	"os/exec"
	"strings"
	"time"
)

//--------------------------------------------------------------------
func Start_mongodb(p_mongodb_bin_path_str string,
	p_mongodb_port_str int,
	p_mongodb_data_dir_path_str string,
	p_mongodb_log_file_path_str string,
	p_sudo_bool bool,
	p_log_fun func(string, string)) error {
	p_log_fun("FUN_ENTER", "gf_ops_daemon_init.Start_mongodb()")
	p_log_fun("INFO", "p_mongodb_data_dir_path_str - "+p_mongodb_data_dir_path_str)
	p_log_fun("INFO", "p_mongodb_log_file_path_str - "+p_mongodb_log_file_path_str)

	if _, err := os.Stat(p_mongodb_log_file_path_str); os.IsNotExist(err) {
		p_log_fun("ERROR", "supplied log_file path is not a file - "+p_mongodb_log_file_path_str)
		return err
	}

	p_log_fun("INFO", "-----------------------------------------")
	p_log_fun("INFO", "--------- STARTING - MONGODB ------------")
	p_log_fun("INFO", "-----------------------------------------")
	p_log_fun("INFO", "p_mongodb_bin_path_str      - "+p_mongodb_bin_path_str)
	p_log_fun("INFO", "p_mongodb_data_dir_path_str - "+p_mongodb_data_dir_path_str)
	p_log_fun("INFO", "p_mongodb_log_file_path_str - "+p_mongodb_log_file_path_str)

	args_lst := []string{
		"--fork", //start the server as a deamon
		fmt.Sprintf("--dbpath %s", p_mongodb_data_dir_path_str),
		fmt.Sprintf("--logpath %s", p_mongodb_log_file_path_str),

		"--port " + fmt.Sprint(p_mongodb_port_str),
		"--rest", //turn on REST http API interface
		"--httpinterface",
		"--journal", //turn journaling/durability on

		"--oplogSize 128",
	}

	var cmd *exec.Cmd
	if p_sudo_bool {
		new_args_lst := []string{p_mongodb_bin_path_str}
		new_args_lst = append(new_args_lst, args_lst...)

		cmd = exec.Command("sudo", new_args_lst...)
	} else {
		//cmd = exec.Command("/usr/bin/mongod") //fmt.Sprintf("'%s'",strings.Join(args_lst," ")),"&")
		cmd = exec.Command(p_mongodb_bin_path_str, args_lst...)
	}

	p_log_fun("INFO", "cmd - "+strings.Join(cmd.Args, " "))
	cmd.Start()

	return nil
}

//-------------------------------------------------
func Conn_to_mongodb(p_mongodb_host_str string,
	p_mongodb_db_name_str string,
	p_log_fun func(string, string)) *mgo.Database {
	p_log_fun("FUN_ENTER", "gf_mongodb.Conn_to_mongodb()")
	p_log_fun("INFO", "p_mongodb_host_str    - "+p_mongodb_host_str)
	p_log_fun("INFO", "p_mongodb_db_name_str - "+p_mongodb_db_name_str)

	session, err := mgo.DialWithTimeout(p_mongodb_host_str,
		time.Second*90)
	if err != nil {
		panic(err)
	}

	//--------------------
	//IMPORTANT!! - writes are waited for to confirm them.
	//				in unsafe mode writes are fire-and-forget with no error checking.
	//              this mode is faster, since no confirmation is expected.
	session.SetSafe(&mgo.Safe{})

	//Monotonic consistency - will read from a slave in possible, for better load distribution.
	//                        once the first write happens the connection is switched to the master.
	session.SetMode(mgo.Monotonic, true)
	//--------------------

	db := session.DB(p_mongodb_db_name_str)
	return db
}

//-------------------------------------------------
func Get_rs_members_info(p_mongodb_primary_host_str string,
	p_log_fun func(string, string)) ([]map[string]interface{}, error) {
	p_log_fun("FUN_ENTER", "gf_mongodb.Get_rs_members_info()")
	p_log_fun("INFO", p_mongodb_primary_host_str)

	mongo_client__cmd_str := fmt.Sprintf("mongo --host %s --quiet --eval 'JSON.stringify(rs.status())'",
		p_mongodb_primary_host_str)

	out, err := exec.Command("sh", "-c", mongo_client__cmd_str).Output()

	//---------------
	//JSON
	var i map[string]interface{}
	err = json.Unmarshal([]byte(out), &i)
	if err != nil {
		return nil, err
	}
	//---------------

	rs_members_lst := i["members"].([]map[string]interface{})
	var rs_members_info_lst []map[string]interface{}

	for _, m := range rs_members_lst {

		member_info_map := map[string]interface{}{
			"host_port_str": m["name"].(string),
			"state_str":     m["stateStr"].(string),
			"uptime_int":    m["uptime"].(int),
		}

		rs_members_info_lst = append(rs_members_info_lst, member_info_map)
	}

	return rs_members_info_lst, nil
}
