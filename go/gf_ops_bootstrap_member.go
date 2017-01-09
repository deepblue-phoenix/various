//README - utility functions for working with cluster

package main

import (
	"gf_core"
	"gopkg.in/mgo.v2"
)

//-------------------------------------------------
func bootstrap_member(p_member_node_meta *Gf_cluster_node,
	p_docker_port_str *string,
	p_docker_kv_store__etcd__host_port_str *string,
	p_docker_config_path_str *string,
	p_docker_host_labels_lst []string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) {
	//p_docker_port_str                      = "2375",
	//p_docker_config_path_str               = "/etc/default/docker",
	//p_docker_kv_store__etcd__host_port_str = None) {
	p_log_fun("FUN_ENTER", "gf_ops_bootstrap_member.bootstrap_member()")

	ssh__user_str := "root"
	host_str := p_member_node_meta.host_str
	docker_host_labels_lst := p_member_node_meta.labels_lst

	//-------------------------------------------------
	//CLEANUP

	//IMPORTANT!! - remove any /etc/default/docker files from previous runs
	if gf_core.Ssh__file_exists(p_docker_config_path_str,
		&ssh__user_str,
		&host_str,
		p_log_fun) {
		gf_core.Ssh_run_cmd("rm "+*p_docker_config_path_str,
			&ssh__user_str,
			&host_str,
			p_log_fun)
	}

	//in case apt-get was interupted at some point, and left a lock file.
	//if its not removed install_base_docker() will fail
	f_str := "/var/lib/dpkg/lock"
	if gf_core.Ssh__file_exists(&f_str,
		&ssh__user_str,
		&host_str,
		p_log_fun) {
		gf_core.Ssh_run_cmd("rm /var/lib/dpkg/lock", &ssh__user_str, &host_str, p_log_fun)
	}
	//-------------------------------------------------

	//INSTALL
	gf_core.Docker__install_base(&ssh__user_str,
		&host_str,
		p_log_fun)

	//CONFIG
	gf_core.Docker__config_remote_deamon(p_docker_port_str,
		docker_host_labels_lst,
		p_docker_kv_store__etcd__host_port_str,
		p_docker_config_path_str,
		&ssh__user_str,
		&host_str,
		p_log_fun)
	/*//----------------------------
	//JOIN SWARM CLUSTER
	member_host_str = p_member_node_phy_adt.hosts_dict["public"]
	join_node_to_swarm_cluster(member_host_str,
							p_mongodb_coll,
							p_log_fun)
	//----------------------------*/
}

//-------------------------------------------------
func join_node_to_swarm_cluster(p_member_node_host_str *string,
	p_member_host_str *string,
	p_docker_port_str *string,
	p_docker_kv_store__etcd__host_port_str *string,
	p_ssh__host_str *string,
	p_ssh__user_str *string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) error {
	p_log_fun("FUN_ENTER", "gf_ops_bootstrap_member.join_node_to_swarm_cluster()")

	//-----------------
	//GET SWARM_CLUSTER_ID
	swarm_cluster_info_map, err := gf_core.Swarm__db_get_cluster_info(p_mongodb_coll,
		p_log_fun)
	if err != nil {
		return err
	}
	swarm_cluster_id_str := swarm_cluster_info_map["swarm_cluster_id_str"].(string)
	//-----------------

	gf_core.Swarm__join_node_to_cluster(&swarm_cluster_id_str,
		p_member_host_str,
		p_docker_port_str,
		p_docker_kv_store__etcd__host_port_str,
		p_ssh__host_str,
		p_ssh__user_str,
		p_log_fun)
	return nil
}
