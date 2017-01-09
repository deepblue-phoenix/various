//README - utility functions for working with my cluster

package main

import (
	"gf_core"
)

//-------------------------------------------------
func boostrap_master(p_master_node_meta *Gf_cluster_node,
	p_cluster_name_str *string,
	p_docker_port_str *string,
	p_docker_overlay_net_name_str *string,
	p_docker_config_path_str *string,
	p_swarm_manager_port_str *string,
	p_log_fun func(string, string)) {
	p_log_fun("FUN_ENTER", "gf_ops_bootstrap_master.boostrap_master()")

	mongo_db := gf_core.Conn_to_mongodb("127.0.0.1", //p_mongodb_host_str,
		"gf_ops", //p_mongodb_db_name_str   string,
		p_log_fun)

	ssh__user_str := "root"
	docker_host_labels_lst := p_master_node_meta.labels_lst
	host_str := p_master_node_meta.host_str
	docker_kv_store__etcd__host_port_str := p_master_node_meta.docker_kv_store__etcd__host_port_str
	//---------------------
	gf_core.Ssh_run_cmd("apt-get update", &ssh__user_str, &host_str, p_log_fun)
	//---------------------
	//CREATE USER

	//"-p" - Create any missing intermediate pathname components
	gf_core.Ssh_run_cmd("mkdir -p /home/gf", &ssh__user_str, &host_str, p_log_fun)
	gf_core.Ssh_run_cmd("useradd gf", &ssh__user_str, &host_str, p_log_fun)
	//---------------------
	//INSTALL PYTHON - its no longer installed by default in ubuntu 15.10
	gf_core.Ssh_run_cmd("apt-get install -y python-minimal", &ssh__user_str, &host_str, p_log_fun)
	//---------------------
	//DOCKER

	p_log_fun("INFO", ">>>>>>>>>>>>------------------------------------------->>>>>>>>>>>>>")
	p_log_fun("INFO", "INIT DOCKER")
	p_log_fun("INFO", ">>>>>>>>>>>>------------------------------------------->>>>>>>>>>>>>")

	//if this is run on an already initialized node, make sure you kill docker first,
	//to run a clean install
	//IMPORTANT!! - use single-quotes instead of double, for "'print $1'", because
	//              otherwise bash will start interpreting "$" in the AWK expression
	gf_core.Ssh_run_cmd("sudo kill -9 `ps -e | grep docker | awk {'print $1'}`", &ssh__user_str, &host_str, p_log_fun)

	setup_docker__kv_store(p_log_fun)

	//INSTALL
	gf_core.Docker__install_base(&ssh__user_str,
		&host_str,
		p_log_fun)

	//CONFIG
	gf_core.Docker__config_remote_deamon(p_docker_port_str,
		docker_host_labels_lst,
		&docker_kv_store__etcd__host_port_str,
		p_docker_config_path_str,
		&ssh__user_str,
		&host_str,
		p_log_fun)
	//OVERLAY_NETWORK
	gf_core.Docker__create_overlay_network(p_docker_overlay_net_name_str,
		&ssh__user_str,
		&host_str,
		p_log_fun)
	//---------------------
	//SWARM CREATE CLUSTER

	p_log_fun("INFO", ">>>>>>>>>>>>------------------------------------------->>>>>>>>>>>>>")
	p_log_fun("INFO", "INIT SWARM")
	p_log_fun("INFO", ">>>>>>>>>>>>------------------------------------------->>>>>>>>>>>>>")

	swarm_cluster_id_str, _ := gf_core.Swarm__create_cluster(&ssh__user_str,
		&host_str,
		p_log_fun)

	//DB PERSIST
	gf_core.Swarm__db_create_cluster_info(p_cluster_name_str,
		swarm_cluster_id_str,
		mongo_db,
		p_log_fun)
	//---------------------
	//START SWARM MANAGER

	p_log_fun("INFO", ">>>>>>>>>>>>------------------------------------------->>>>>>>>>>>>>")
	p_log_fun("INFO", "START SWARM MANAGER")
	p_log_fun("INFO", ">>>>>>>>>>>>------------------------------------------->>>>>>>>>>>>>")

	gf_core.Swarm__init_manager(swarm_cluster_id_str,
		p_swarm_manager_port_str,
		&ssh__user_str,
		&host_str,
		p_log_fun)
	//---------------------
	gf_core.Ssh_run_cmd("apt-get install -y nmap", &ssh__user_str, &host_str, p_log_fun)
}

//-------------------------------------------------
func setup_docker__kv_store(p_log_fun func(string, string)) {
	p_log_fun("FUN_ENTER", "gf_ops_bootstrap_master.setup_docker__kv_store()")
}
