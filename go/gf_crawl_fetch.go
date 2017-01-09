package gf_crawl_lib

import (
	"fmt"
	"time"
	"net/url"
	"net/http"

	//"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
	//"github.com/aws/aws-sdk-go/service/s3"
	//"github.com/aws/aws-sdk-go/service/s3/s3manager"
	//"gopkg.in/olivere/elastic.v3"
	"github.com/PuerkitoBio/goquery"
	"github.com/fatih/color"
	
	"gf_core"
)
//--------------------------------------------------
//ELASTIC_SEARCH - INDEXED
type Crawler_url_fetch struct {
	Id                   bson.ObjectId     `bson:"_id,omitempty"`
	Id_str               string            `bson:"id_str"               json:"id_str"`
	T_str                string            `bson:"t"                    json:"t"` //"crawler_url_fetch"
	Creation_unix_time_f float64           `bson:"creation_unix_time_f" json:"creation_unix_time_f"`
	Cycle_run_id_str     string            `bson:"cycle_run_id_str"     json:"cycle_run_id_str"`
	Domain_str           string            `bson:"domain_str"           json:"domain_str"`
	Url_str              string            `bson:"url_str"              json:"url_str"`
	Start_time_f         float64           `bson:"start_time_f"         json:"-"`
	End_time_f           float64           `bson:"end_time_f"           json:"-"`
	Page_text_str        string            `bson:"page_text_str"        json:"page_text_str"` //full text of the page html - indexed in ES
	goquery_doc          *goquery.Document `bson:"-"                    json:"-"`

	//-------------------
	//IMPORTANT!! - last error that occured/interupted processing of this link
	Error_type_str       string            `bson:"error_type_str,omitempty"`
	Error_id_str         string            `bson:"error_id_str,omitempty"`
	//-------------------
}
//--------------------------------------------------
func fetch_url(p_url_str string,
		p_link             *Crawler_page_outgoing_link,
		p_cycle_run_id_str *string,
		p_crawler_name_str *string,
		p_runtime          *Crawler_runtime,
		p_log_fun          func(string,string)) (*Crawler_url_fetch,*string,error) {
	p_log_fun("FUN_ENTER","gf_crawl_fetch.fetch_url()")

	cyan   := color.New(color.FgCyan).SprintFunc()
	yellow := color.New(color.FgYellow).SprintFunc()

	p_log_fun("INFO",cyan(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"))
	p_log_fun("INFO","FETCHING >> - "+yellow(p_url_str))
	p_log_fun("INFO",cyan(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"))


	start_time_f := float64(time.Now().UnixNano())/1000000000.0

	//-------------------
	url,_                := url.Parse(p_url_str)
	domain_str           := url.Host
	creation_unix_time_f := float64(time.Now().UnixNano())/1000000000.0
	id_str               := "crawler_fetch__"+fmt.Sprint(creation_unix_time_f)
	fetch                := &Crawler_url_fetch{
		Id_str              :id_str,
		T_str               :"crawler_url_fetch",
		Creation_unix_time_f:creation_unix_time_f,
		Cycle_run_id_str    :*p_cycle_run_id_str,
		Domain_str          :domain_str,
		Url_str             :p_url_str,
		Start_time_f        :start_time_f,
		//End_time_f          :end_time_f,
		//Page_text_str       :doc.Text(),
		//goquery_doc         :doc,
	}

	err := p_runtime.Mongodb_coll.Insert(fetch)
	if err != nil {
		t:="fetch_url__failed"
		m:="failed to DB persist Crawler_url_fetch struct of fetch for url - "+p_url_str
		crawler_error,ce_err := create_error_and_event(&t,&m,map[string]interface{}{},&p_url_str,p_crawler_name_str,
											p_runtime,p_log_fun)
		if ce_err != nil {
			return nil,nil,ce_err
		}

		if p_link != nil {
			//IMPORTANT!! - mark link as failed, so that it is not repeatedly tried
			lm_err := link__mark_as_failed(crawler_error,
									p_link,
									p_runtime,
									p_log_fun)
			if lm_err != nil {
				return nil,nil,lm_err
			}
		}

		return nil,nil,err
	}
	//-------------------
	//HTTP REQUEST

	doc,err := make__http_request(p_url_str,
							p_log_fun)

	if err != nil {
		t:="fetch_url__failed"
		m:="failed to HTTP fetch url - "+p_url_str
		crawler_error,ev_err := create_error_and_event(&t,&m,map[string]interface{}{},&p_url_str,p_crawler_name_str,
											p_runtime,p_log_fun)
		if ev_err != nil {
			return nil,nil,ev_err
		}

		if p_link != nil {

			//IMPORTANT!! - mark link as failed, so that it is not repeatedly tried
			lm_err := link__mark_as_failed(crawler_error,
									p_link,
									p_runtime,
									p_log_fun)
			if lm_err != nil {
				return nil,nil,lm_err
			}
		}

		fetch__mark_as_failed(crawler_error,
						fetch,
						p_runtime,
						p_log_fun)

		return nil,nil,err
	}

	end_time_f := float64(time.Now().UnixNano())/1000000000.0
	//-------------
	//UPDATE FETCH
	fetch.End_time_f    = end_time_f
	fetch.Page_text_str = doc.Text()
	fetch.goquery_doc   = doc
	err = p_runtime.Mongodb_coll.Update(bson.M{"id_str":fetch.Id_str,"t":"crawler_url_fetch"},
								bson.M{"$set":bson.M{
									"end_time_f"   :end_time_f,
									"page_text_str":doc.Text(),
								}})
	if err != nil {
		return nil,nil,err
	}
	//-------------
	//SEND_EVENT
	if p_runtime.Events_ctx != nil {
		events_id_str  := "crawler_events"
		event_type_str := "fetch__http_request__done"
		msg_str        := "completed fetching a document over HTTP"
		data_map       := map[string]interface{}{
			"url_str"     :p_url_str,
			"start_time_f":start_time_f,
			"end_time_f"  :end_time_f,
		}

		gf_core.Events__send_event(events_id_str,
							event_type_str, //p_type_str
							msg_str,        //p_msg_str
							data_map,
							p_runtime.Events_ctx,
							p_log_fun)
	}

	return fetch,&domain_str,nil
}
//--------------------------------------------------
func make__http_request(p_url_str string,
					p_log_fun func(string,string)) (*goquery.Document,error) {
	p_log_fun("FUN_ENTER","gf_crawl_fetch.make__http_request()")

	/*res,err := http.Get(p_url_str)
	if err != nil {
		p_log_fun("ERROR","failed fetching the url - "+p_url_str)
		p_log_fun("ERROR",fmt.Sprint(err))
		return nil,err
	}*/

	client := &http.Client{
		/*IMPORTANT!! - golang http lib does not copy user-set headers on redirects, so a manual
		                setting of these headers had to be added, via the CheckRedirect function
		                that gets called on every redirect, which gives us a chance to to re-set
		                user-agent headers again to the correct value*/
		/*CheckRedirect specifies the policy for handling redirects.
        If CheckRedirect is not nil, the client calls it before
        following an HTTP redirect. The arguments req and via are
        the upcoming request and the requests made already, oldest
        first. If CheckRedirect returns an error, the Client's Get
        method returns both the previous Response (with its Body
        closed) and CheckRedirect's error (wrapped in a url.Error)
        instead of issuing the Request req.
        As a special case, if CheckRedirect returns ErrUseLastResponse,
        then the most recent response is returned with its body
        unclosed, along with a nil error.
        If CheckRedirect is nil, the Client uses its default policy,
        which is to stop after 10 consecutive requests.*/
		CheckRedirect:func(req *http.Request, via []*http.Request) error {
			req.Header.Del("User-Agent")
			req.Header.Set("User-Agent","use-some-user-agent-string")
			return nil
		},
	}

	req, err := http.NewRequest("GET",p_url_str, nil)
	if err != nil {
		p_log_fun("ERROR",fmt.Sprint(err))
		return nil,err
	}

	req.Header.Del("User-Agent")
	req.Header.Set("User-Agent","use-some-user-agent-string")


	resp,err := client.Do(req)
	if err != nil {
		p_log_fun("ERROR",fmt.Sprint(err))
		return nil,err
	}

	//doc,err := goquery.NewDocument(p_url_str)od kad sam ustao 
	doc,err := goquery.NewDocumentFromResponse(resp)
	if err != nil {
		return nil,err
	}

	return doc,nil
}
//--------------------------------------------------
func parse_fech_result(p_url_fetch *Crawler_url_fetch,
				p_cycle_run_id_str   *string,
				p_crawler_name_str   *string,
				p_s3_bucket_name_str string,
				p_runtime            *Crawler_runtime,
				p_log_fun            func(string,string)) error {
	p_log_fun("FUN_ENTER","gf_crawl_fetch.parse_fech_result()")

	//----------------
	//GET LINKS
	links__get_outgoing_in_page(p_url_fetch,
						p_cycle_run_id_str,
						p_crawler_name_str,
						p_runtime,
						p_log_fun)
	//----------------
	//GET IMAGES
	err := images__get_in_page(p_url_fetch,
					p_cycle_run_id_str,
					p_crawler_name_str,
					p_s3_bucket_name_str,
					p_runtime,
					p_log_fun)
	if err != nil {
		return err
	}
	//----------------
	//INDEX URL_FETCH
	err = index__build__of_url_fetch(p_url_fetch,
							p_runtime,
							p_log_fun)

	if err != nil {
		return err
	}
	//----------------

	return nil
}
//--------------------------------------------------
func fetch__mark_as_failed(p_error *Crawler_error,
					p_fetch   *Crawler_url_fetch,
					p_runtime *Crawler_runtime,
					p_log_fun func(string,string)) error {
	p_log_fun("FUN_ENTER","gf_crawl_fetch.fetch__mark_as_failed()")

	p_fetch.Error_id_str   = p_error.Id_str
	p_fetch.Error_type_str = p_error.Type_str

	err := p_runtime.Mongodb_coll.Update(bson.M{
					"id_str":p_fetch.Id_str,
					"t"     :"crawler_url_fetch",
				},
				bson.M{"$set":bson.M{
						"error_id_str"  :p_error.Id_str,
						"error_type_str":p_error.Type_str,
					},
				})
	if err != nil {
		return err
	}

	return nil
}