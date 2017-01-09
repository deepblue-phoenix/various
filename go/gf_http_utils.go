//README - HTTP utility functions

package gf_core

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
)

//-------------------------------------------------
func HTTP__init_static_serving(p_url_base_str *string,
	p_log_fun func(string, string)) {
	p_log_fun("FUN_ENTER", "gf_http_utils.HTTP__init_static_serving()")

	//IMPORTANT!! - trailing "/" in this url spec is important, since the desired urls that should
	//              match this are /audiencenet/track/static/some_further_text, and those will only match
	//              if the spec here ends with "/"
	url_str := *p_url_base_str + "/static/"
	http.HandleFunc(url_str, func(p_resp http.ResponseWriter,
		p_req *http.Request) {
		//fmt.Println("FILE SERVE >>>>>>>>")

		if p_req.Method == "GET" {
			path_str := p_req.URL.Path
			file_path_str := strings.Replace(path_str, url_str, "", 1) //"1" - just replace one occurance
			local_path_str := "./static/" + file_path_str

			p_log_fun("INFO", "file_path_str  - "+file_path_str)
			p_log_fun("INFO", "local_path_str - "+local_path_str)

			http.ServeFile(p_resp,
				p_req,
				local_path_str)
		}
	})
}

//-------------------------------------------------
func HTTP__serialize_cookies(p_cookies_lst []*http.Cookie,
	p_log_fun func(string, string)) *string {
	p_log_fun("FUN_ENTER", "gf_http_utils.HTTP__serialize_cookies()")

	buffer := bytes.NewBufferString("")
	for _, cookie := range p_cookies_lst {
		cookie_str := cookie.Raw
		buffer.WriteString("; " + cookie_str)
	}
	cookies_str := buffer.String()
	return &cookies_str
}

//-------------------------------------------------
func HTTP__init_sse(p_resp http.ResponseWriter,
	p_log_fun func(string, string)) (http.Flusher, error) {
	p_log_fun("FUN_ENTER", "gf_http_utils.HTTP__init_sse()")

	flusher, ok := p_resp.(http.Flusher)
	if !ok {
		err_msg_str := "GF - sse streaming not supported by this server"
		http.Error(p_resp, err_msg_str, http.StatusInternalServerError)
		return nil, errors.New(err_msg_str)
	}

	//IMPORTANT!! - listening for the closing of the http connections
	notify := p_resp.(http.CloseNotifier).CloseNotify()
	go func() {
		p_log_fun("INFO", "HTTP SSE CONNECTION CLOSED")
		<-notify
	}()

	p_resp.Header().Set("Content-Type", "text/event-stream")
	p_resp.Header().Set("Cache-Control", "no-cache")
	p_resp.Header().Set("Connection", "keep-alive")
	p_resp.Header().Set("Access-Control-Allow-Origin", "*")

	flusher.Flush()

	return flusher, nil
}

//-------------------------------------------------
func HTTP__get_streaming_response(p_url_str string,
	p_log_fun func(string, string)) (*[]map[string]interface{}, error) {
	p_log_fun("FUN_ENTER", "gf_http_utils.HTTP__get_streaming_response()")

	req, err := http.NewRequest("GET", p_url_str, nil)
	req.Header.Set("accept", "text/event-stream")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}

	//resp, err := http.Get(p_url_str)
	//if err != nil {
	//	return nil,err
	//}

	data_lst := []map[string]interface{}{}
	reader := bufio.NewReader(resp.Body)
	for {
		line_lst, err := reader.ReadBytes('\n')
		if err != nil {
			return nil, err
		}

		line_str := string(line_lst)

		if strings.HasPrefix(line_str, "data: ") {
			clean_line_str := strings.Replace(line_str, "data: ", "", 1)

			data_map := map[string]interface{}{}
			err := json.Unmarshal([]byte(clean_line_str), &data_map)

			if err != nil {
				return nil, err
			}

			data_lst = append(data_lst, data_map)
		}
	}

	return &data_lst, nil
}
