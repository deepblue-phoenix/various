package gf_images_lib

import (
	"fmt"
	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
	"time"

	"gf_stats"
)

//-------------------------------------------------
func Stats_init(p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) {
	p_log_fun("FUN_ENTER", "gf_images_stats.Stats_init()")

	stats_funs_map := map[string]interface{}{
		"image_jobs_errors":                  stats__image_jobs_errors,
		"completed_image_jobs_runtime_infos": stats__completed_image_jobs_runtime_infos,
	}

	gf_stats.Init("/images/stats",
		stats_funs_map,
		p_mongodb_coll,
		p_log_fun)
}

//-------------------------------------------------
func stats__image_jobs_errors(p_run_id_str *string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (*gf_stats.Stat_run__results, error) {
	p_log_fun("FUN_ENTER", "gf_images_stats.stats__image_jobs_errors()")

	start_time__unix_f := float64(time.Now().UnixNano()) / 1000000000.0

	pipe := p_mongodb_coll.Pipe([]bson.M{
		bson.M{"$match": bson.M{
			"t":            "img_running_job",
			"start_time_f": bson.M{"$exists": true}, //filter for new start_time_f/end_time_f format
		},
		},

		bson.M{"$project": bson.M{
			"id_str":       true,
			"errors_lst":   true,
			"start_time_f": true, //include field
			"errors_num_i": bson.M{"$size": "$errors_lst"},
		},
		},
		bson.M{"$sort": bson.M{
			"start_time_f": 1,
		},
		},
	})

	results_lst := []map[string]interface{}{}
	err := pipe.All(&results_lst)

	if err != nil {
		p_log_fun("ERROR", fmt.Sprint(err))
		return nil, err
	}

	end_time__unix_f := float64(time.Now().UnixNano()) / 1000000000.0

	data_map := map[string]interface{}{
		"image_jobs_errors_lst": results_lst,
	}

	stat_result := &gf_stats.Stat_run__results{
		Id_str:             *p_run_id_str,
		Data_map:           data_map,
		Start_time__unix_f: start_time__unix_f,
		End_time__unix_f:   end_time__unix_f,
	}

	return stat_result, nil
}

//-------------------------------------------------
func stats__completed_image_jobs_runtime_infos(p_run_id_str *string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (*gf_stats.Stat_run__results, error) {
	p_log_fun("FUN_ENTER", "gf_images_stats.stats__completed_image_jobs_runtime_infos()")

	start_time__unix_f := float64(time.Now().UnixNano()) / 1000000000.0

	pipe := p_mongodb_coll.Pipe([]bson.M{
		bson.M{"$match": bson.M{
			"t":            "img_running_job",
			"status_str":   "complete",
			"start_time_f": bson.M{"$exists": true}, //filter for new start_time_f/end_time_f format
		},
		},
		bson.M{"$project": bson.M{
			"_id":                    false, //suppression of the "_id" field
			"status_str":             true,  //include field
			"start_time_f":           true,  //include field
			"end_time_f":             true,  //include field
			"runtime_duration_sec_f": bson.M{"$subtract": []string{"$end_time_f", "$start_time_f"}},
			"processed_imgs_num_i":   bson.M{"$size": "$images_urls_to_process_lst"},
		},
		},
		bson.M{"$sort": bson.M{"start_time_f": 1}},
	})

	/*var results_lst []map[string]interface{}
	  err := p_mongodb_coll.Find(bson.M{"obj_class_str":"img_running_job",}).
	  				Sort("-start_time__unix_str"). //descending:true
	  				All(&results_lst)

	  if err != nil {
	      return nil,err
	  }*/

	results_lst := []map[string]interface{}{}
	err := pipe.All(&results_lst)

	if err != nil {
		p_log_fun("ERROR", fmt.Sprint(err))
		return nil, err
	}

	end_time__unix_f := float64(time.Now().UnixNano()) / 1000000000.0

	data_map := map[string]interface{}{
		"completed_image_jobs_runtime_infos_lst": results_lst,
	}

	stat_result := &gf_stats.Stat_run__results{
		Id_str:             *p_run_id_str,
		Data_map:           data_map,
		Start_time__unix_f: start_time__unix_f,
		End_time__unix_f:   end_time__unix_f,
	}

	return stat_result, nil
}
