//README - part of an image-processing job server

package gf_images_lib

import (
	"errors"
	"fmt"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/s3/s3manager"
	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
	"time"
)

//-------------------------------------------------
type Job_msg struct {
	job_id_str            string
	client_type_str       string
	cmd_str               string //"start_job"|"get_running_job_ids"
	msg_response_ch       chan interface{}
	job_updates_ch        chan *Job_update_msg
	images_to_process_lst []Image_to_process
	flow_name_str         string
}
type Image_to_process struct {
	Source_url_str      string `bson:"source_url_str"`
	Origin_page_url_str string `bson:"origin_page_url_str"`
}

type Job_update_msg struct {
	Type_str             string        `json:"type_str"`
	Image_id_str         string        `json:"image_id_str"`
	Image_source_url_str string        `json:"image_source_url_str"`
	Err_str              string        `json:"err_str,omitempty"` //if the update indicates an error, this is its value
	Image_thumbs         *Image_thumbs `json:"-"`
}

type Running_job struct {
	Id                    bson.ObjectId        `bson:"_id,omitempty"`
	Id_str                string               `bson:"id_str"`
	T_str                 string               `bson:"t"`
	Client_type_str       string               `bson:"client_type_str"`
	Status_str            string               `bson:"status_str"` //"running"|"complete"
	Start_time_f          float64              `bson:"start_time_f"`
	End_time_f            float64              `bson:"end_time_f"`
	Images_to_process_lst []Image_to_process   `bson:"images_to_process_lst"`
	Errors_lst            []Job_Error          `bson:"errors_lst"`
	job_updates_ch        chan *Job_update_msg `bson:"-"`
}

type Job_Error struct {
	Type_str             string `bson:"type_str"`  //"fetcher_error"|"transformer_error"
	Error_str            string `bson:"error_str"` //serialization of the golang error
	Image_source_url_str string `bson:"image_source_url_str"`
}

//called "expected" because jobs are long-running processes, and they might fail at various stages
//of their processing. in that case some of these result values will be satisfied, others will not.
type Job_Expected_Output struct {
	Image_id_str                      string `json:"image_id_str"`
	Image_source_url_str              string `json:"image_source_url_str"`
	Thumbnail_small_relative_url_str  string `json:"thumbnail_small_relative_url_str"`
	Thumbnail_medium_relative_url_str string `json:"thumbnail_medium_relative_url_str"`
	Thumbnail_large_relative_url_str  string `json:"thumbnail_large_relative_url_str"`
}

//-------------------------------------------------
//CLIENT
//-------------------------------------------------
func start_job(p_client_type_str string,
	p_images_to_process_lst []Image_to_process,
	p_flow_name_str string,
	p_jobs_mngr_ch chan Job_msg,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (*Running_job, []*Job_Expected_Output, error) {
	p_log_fun("FUN_ENTER", "gf_images_jobs.start_job()")
	p_log_fun("INFO", "p_images_to_process_lst - "+fmt.Sprint(p_images_to_process_lst))

	job_cmd_str := "start_job"
	job_start_time_f := float64(time.Now().UnixNano()) / 1000000000.0
	job_id_str := fmt.Sprintf("job:%f", job_start_time_f)
	job_updates_ch := make(chan *Job_update_msg, 10)

	Job_msg := Job_msg{
		job_id_str:            job_id_str,
		client_type_str:       p_client_type_str,
		cmd_str:               job_cmd_str,
		job_updates_ch:        job_updates_ch,
		images_to_process_lst: p_images_to_process_lst,
		flow_name_str:         p_flow_name_str,
	}

	p_jobs_mngr_ch <- Job_msg
	//-----------------
	//CREATE RUNNING_JOB
	running_job := &Running_job{
		Id_str:                job_id_str,
		T_str:                 "img_running_job",
		Client_type_str:       p_client_type_str,
		Status_str:            "running",
		Start_time_f:          job_start_time_f,
		Images_to_process_lst: p_images_to_process_lst,
		job_updates_ch:        job_updates_ch,
	}

	err := p_mongodb_coll.Insert(running_job)
	if err != nil {
		p_log_fun("ERROR", "cant persist Running_job struct")
		return nil, nil, err
	}
	//-----------------
	//CREATE JOB_EXPECTED_OUTPUT

	job_expected_outputs_lst := []*Job_Expected_Output{}

	for _, image_to_process := range p_images_to_process_lst {

		img_source_url_str := image_to_process.Source_url_str
		p_log_fun("INFO", "img_source_url_str - "+fmt.Sprint(img_source_url_str))

		//--------------
		//IMAGE_ID
		image_id_str, i_err := Image__create_id_from_url(&img_source_url_str,
			p_log_fun)
		if i_err != nil {
			return nil, nil, i_err
		}
		//--------------
		//GET FILE_FORMAT
		normalized_ext_str, ok, err := Get_image_ext_from_url(&img_source_url_str,
			p_log_fun)
		if err != nil {
			return nil, nil, err
		}

		//IMPORTANT!! - this is run if the image format is unsupported.
		//FIX!!        (maybe it should not fail the whole job if one image is invalid,
		//              it should continue and just murk that image with an error)
		if !ok {
			return nil, nil, errors.New("invalid image extension (" + *normalized_ext_str + ") found in image_info - " + img_source_url_str)
		}
		//--------------

		output := &Job_Expected_Output{
			Image_id_str:                      *image_id_str,
			Image_source_url_str:              img_source_url_str,
			Thumbnail_small_relative_url_str:  fmt.Sprintf("/images/d/thumbnails/%s_thumb_small.%s", *image_id_str, *normalized_ext_str),
			Thumbnail_medium_relative_url_str: fmt.Sprintf("/images/d/thumbnails/%s_thumb_medium.%s", *image_id_str, *normalized_ext_str),
			Thumbnail_large_relative_url_str:  fmt.Sprintf("/images/d/thumbnails/%s_thumb_large.%s", *image_id_str, *normalized_ext_str),
		}
		job_expected_outputs_lst = append(job_expected_outputs_lst, output)
	}
	//-----------------

	return running_job, job_expected_outputs_lst, nil
}

//-------------------------------------------------
func get_running_job_update_ch(p_job_id_str string,
	p_jobs_mngr_ch chan Job_msg,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (chan *Job_update_msg, error) {
	p_log_fun("FUN_ENTER", "gf_images_jobs.get_running_job_update_ch()")

	msg_response_ch := make(chan interface{})
	defer close(msg_response_ch)

	job_cmd_str := "get_running_job_update_ch"
	job_msg := Job_msg{
		job_id_str:      p_job_id_str,
		cmd_str:         job_cmd_str,
		msg_response_ch: msg_response_ch,
	}

	p_jobs_mngr_ch <- job_msg

	response := <-msg_response_ch
	job_updates_ch, _ := response.(chan *Job_update_msg)

	return job_updates_ch, nil
}

//-------------------------------------------------
//SERVER
//-------------------------------------------------
func Jobs_mngr__init(p_images_store_local_dir_path_str *string,
	p_images_thumbnails_store_local_dir_path_str *string,
	p_s3_bucket_name_str *string,
	p_s3_client *s3.S3,
	p_s3_uploader *s3manager.Uploader,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) chan Job_msg {
	p_log_fun("FUN_ENTER", "gf_images_jobs.Jobs_mngr__init()")

	jobs_mngr_ch := make(chan Job_msg, 100)

	//IMPORTANT!! - start jobs_mngr as an independent goroutine of the HTTP handlers at
	//              service initialization time
	go func() {

		running_jobs_map := map[string]chan *Job_update_msg{}

		//listen to messages
		for {
			job_msg := <-jobs_mngr_ch

			//IMPORTANT!! - only one job is processed per jobs_mngr.
			//              Scaling is done with multiple jobs_mngr's (exp. per-core)
			switch job_msg.cmd_str {

			//------------------------
			case "start_job":

				job_id_str := job_msg.job_id_str
				running_jobs_map[job_id_str] = job_msg.job_updates_ch

				run_job_err := jobs_mngr__run_job(job_id_str,
					&job_msg.client_type_str,
					job_msg.images_to_process_lst,
					&job_msg.flow_name_str,
					job_msg.job_updates_ch,
					p_images_store_local_dir_path_str,
					p_images_thumbnails_store_local_dir_path_str,
					p_s3_bucket_name_str,
					p_s3_client,
					p_s3_uploader,
					p_mongodb_coll,
					p_log_fun)
				if run_job_err != nil {
					p_log_fun("ERROR", "run_job_err - "+fmt.Sprint(run_job_err))
				}
				//--------------------
				//MARK JOB AS COMPLETE

				job_end_time_f := float64(time.Now().UnixNano()) / 1000000000.0
				update_err := p_mongodb_coll.Update(bson.M{"t": "img_running_job", "id_str": job_id_str},
					bson.M{
						"$set": bson.M{
							"status_str": "complete",
							"end_time_f": job_end_time_f,
						},
					})
				if update_err != nil {
					p_log_fun("ERROR", "update_err - "+fmt.Sprint(update_err))
				}
				//--------------------

				delete(running_jobs_map, job_id_str) //remove running job from lookup, since its complete
				close(job_msg.job_updates_ch)
			//------------------------
			case "get_running_job_update_ch":

				job_id_str := job_msg.job_id_str

				if _, ok := running_jobs_map[job_id_str]; ok {

					job_updates_ch := running_jobs_map[job_id_str]

					job_msg.msg_response_ch <- job_updates_ch

				} else {
					job_msg.msg_response_ch <- nil
				}
				//------------------------
			}
		}
	}()

	return jobs_mngr_ch
}
