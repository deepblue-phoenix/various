//README - utility functions for working with my server library

package gf_rpc_lib

import (
	"encoding/json"
	"fmt"
	"gopkg.in/mgo.v2"
	"io/ioutil"
	"net/http"

	"gf_core"
)

//-------------------------------------------------
type Gf_rpc_handler_run struct {
	Class_str          string  `bson:"class_str"` //Rpc_Handler_Run
	Handler_url_str    string  `bson:"handler_url_str"`
	Start_time__unix_f float64 `bson:"start_time__unix_f"`
	End_time__unix_f   float64 `bson:"end_time__unix_f"`
}

//-------------------------------------------------
func Get_http_input(p_handler_url_path_str string,
	p_resp http.ResponseWriter,
	p_req *http.Request,
	p_mongo_coll *mgo.Collection,
	p_log_fun func(string, string)) (map[string]interface{}, error) {
	p_log_fun("FUN_ENTER", "gf_rpc_utils.Get_http_input()")

	var i map[string]interface{}
	body_bytes_lst, _ := ioutil.ReadAll(p_req.Body)
	err := json.Unmarshal(body_bytes_lst, &i)
	if err != nil {
		p_log_fun("ERROR", fmt.Sprint(err))
		Error__in_handler(p_handler_url_path_str,
			err,
			"failed parsing http-request input JSON", //p_user_msg_str
			p_resp,
			p_mongo_coll,
			p_log_fun)
		return nil, err
	}

	return i, nil
}

//-------------------------------------------------
func Get_response_format(p_qs_map map[string][]string,
	p_log_fun func(string, string)) string {
	p_log_fun("FUN_ENTER", "gf_rpc_utils.Get_response_format()")

	response_format_str := "html" //default - "h" - HTML
	if f_lst, ok := p_qs_map["f"]; ok {
		response_format_str = f_lst[0] //user supplied value
	}

	return response_format_str
}

//-------------------------------------------------
func Http_Respond(p_data interface{},
	p_status_str string,
	p_resp http.ResponseWriter,
	p_log_fun func(string, string)) {
	p_log_fun("FUN_ENTER", "gf_rpc_utils.Http_Respond()")

	r_lst, _ := json.Marshal(map[string]interface{}{
		"status_str": p_status_str,
		"data":       p_data,
	})
	r_str := string(r_lst)
	fmt.Fprintf(p_resp, r_str)
}

//-------------------------------------------------
func Store_rpc_handler_run(p_handler_url_str string,
	p_start_time__unix_f float64,
	p_end_time__unix_f float64,
	p_mongo_coll *mgo.Collection,
	p_log_fun func(string, string)) error {
	p_log_fun("FUN_ENTER", "gf_rpc_utils.Store_rpc_handler_run()")

	run := &Gf_rpc_handler_run{
		Class_str:          "Rpc_Handler_Run",
		Handler_url_str:    p_handler_url_str,
		Start_time__unix_f: p_start_time__unix_f,
		End_time__unix_f:   p_end_time__unix_f,
	}

	err := p_mongo_coll.Insert(run)
	if err != nil {
		return err
	}

	return nil
}

//-------------------------------------------------
func Error__in_handler(p_handler_url_path_str string,
	p_err error,
	p_usr_msg_str string,
	p_resp http.ResponseWriter,
	p_mongo_coll *mgo.Collection,
	p_log_fun func(string, string)) {
	p_log_fun("FUN_ENTER", "gf_rpc_utils.Error__in_handler()")

	http.Error(p_resp, p_usr_msg_str, http.StatusInternalServerError)

	internal_err_msg_str := fmt.Sprintf("%s handler failed - %s", p_handler_url_path_str, fmt.Sprint(p_err))
	p_log_fun("ERROR", internal_err_msg_str)

	error_map := map[string]string{
		"err_msg_str": internal_err_msg_str,
		"err":         fmt.Sprint(p_err),
		"handler_url_path_str": p_handler_url_path_str,
	}
	gf_core.Persist_error(error_map,
		p_mongo_coll,
		p_log_fun)
	return
}
