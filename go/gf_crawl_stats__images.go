//README - part of my crawler library for use by my applications

package gf_crawl_lib

import (
	"fmt"
	"time"
	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
)
//-------------------------------------------------
type Stat__crawled_images_domain struct {
	Domain_str              string    `bson:"_id"                     json:"domain_str"`
	Imgs_count_int          int       `bson:"imgs_count_int"          json:"imgs_count_int"`
	Creation_unix_times_lst []float64 `bson:"creation_unix_times_lst" json:"creation_unix_times_lst"`
	Urls_lst                []string  `bson:"urls_lst"                json:"urls_lst"`
	Origin_urls_lst         []string  `bson:"origin_urls_lst"         json:"origin_urls_lst"`
	Downloaded_lst          []bool    `bson:"downloaded_lst"          json:"downloaded_lst"`
	Valid_for_usage_lst     []bool    `bson:"valid_for_usage_lst"     json:"valid_for_usage_lst"`
	S3_stored_lst           []bool    `bson:"s3_stored_lst"           json:"s3_stored_lst"`
}

type Stat__crawled_gifs struct {
	Domain_str             string                   `bson:"_id"                    json:"domain_str"`
	Imgs_count_int         int                      `bson:"imgs_count_int"         json:"imgs_count_int"`
	Urls_by_origin_url_lst []map[string]interface{} `bson:"urls_by_origin_url_lst" json:"urls_by_origin_url_lst"`
}

type Stat__recent_images struct {
	Domain_str         string    `bson:"_id"                json:"domain_str"`
	Imgs_count_int     int       `bson:"imgs_count_int"     json:"imgs_count_int"`
	Creation_times_lst []float64 `bson:"creation_times_lst" json:"creation_times_lst"`
	Urls_lst           []string  `bson:"urls_lst"           json:"urls_lst"`
	Nsfv_lst           []bool    `bson:"nsfv_lst"           json:"nsfv_lst"`
}
//-------------------------------------------------
func stats__recent_images(p_mongodb_coll *mgo.Collection,
				p_log_fun func(string,string)) ([]Stat__recent_images,error) {
	p_log_fun("FUN_ENTER","gf_crawl_stats__images.stats__recent_images()")




	start_time__unix_f := float64(time.Now().UnixNano())/1000000000.0

	pipe := p_mongodb_coll.Pipe([]bson.M{
		bson.M{"$match":bson.M{
				"t":"crawler_page_img",
			},
		},

		bson.M{"$sort":bson.M{
				"creation_unix_time_f":-1,
			},
		},

		bson.M{"$limit":1000},

		bson.M{"$group":bson.M{
				"_id"               :"$domain_str",
				"imgs_count_int"    :bson.M{"$sum" :1},
				"creation_times_lst":bson.M{"$push":"$creation_unix_time_f"},
				"urls_lst"          :bson.M{"$push":"$url_str"},
				"nsfv_ls"           :bson.M{"$push":"$nsfv_bool"},
			},
		},
	})

	results_lst := []Stat__recent_images{}
	err         := pipe.All(&results_lst)

	if err != nil {
		p_log_fun("ERROR",fmt.Sprint(err))
		return nil,err
	}

	end_time__unix_f := float64(time.Now().UnixNano())/1000000000.0

	//------------------
	var r interface{}
	r = results_lst
	create__stat_run("crawler_recent_images",r,start_time__unix_f,end_time__unix_f,p_mongodb_coll,p_log_fun)
	//------------------

	return results_lst,nil
}
//-------------------------------------------------
func stats__gifs_by_days(p_mongodb_coll *mgo.Collection,
					p_log_fun func(string,string)) (*Stats__objs_by_days,error) {
	p_log_fun("FUN_ENTER","gf_crawl_stats__images.stats__gifs_by_days()")


	stats__fetches_by_days,err := stats__objs_by_days(map[string]interface{}{"img_ext_str":"gif",},
												"crawler_page_img",
												p_mongodb_coll,
												p_log_fun)
	if err != nil {
		return nil,err
	}

	return stats__fetches_by_days,nil
}
//-------------------------------------------------
func stats__gifs(p_mongodb_coll *mgo.Collection,
			p_log_fun func(string,string)) ([]Stat__crawled_gifs,error) {
	p_log_fun("FUN_ENTER","gf_crawl_stats__images.stats__gifs()")

	start_time__unix_f := float64(time.Now().UnixNano())/1000000000.0

	pipe := p_mongodb_coll.Pipe([]bson.M{
		bson.M{"$match"  :bson.M{
				"t"          :"crawler_page_img",
				"img_ext_str":"gif",
			},
		},

		bson.M{"$project":bson.M{
				"domain_str"          :true,
				"creation_unix_time_f":true,
				"origin_url_str"      :true,
				"url_str"             :true,
				"nsfv_bool"           :true,
			},
		},

		bson.M{"$group":bson.M{
				"_id"               :bson.M{"origin_url_str":"$origin_url_str","domain_str":"$domain_str",},
				"creation_times_lst":bson.M{"$push":"$creation_unix_time_f"},
				"urls_lst"          :bson.M{"$push":"$url_str"},
				"nsfv_lst"          :bson.M{"$push":"$nsfv_bool"},
				"count_int"         :bson.M{"$sum" :1},
			},
		},

		bson.M{"$group":bson.M{
				"_id"                   :"$_id.domain_str",
				"imgs_count_int"        :bson.M{"$sum" :"$count_int",}, //add up counts from the previous grouping operation
				"urls_by_origin_url_lst":bson.M{"$push":bson.M{
								"origin_url_str"    :"$_id.origin_url_str",
								"creation_times_lst":"$creation_times_lst",
								"urls_lst"          :"$urls_lst",
								"nsfv_lst"          :"$nsfv_lst",
							},
						},
			},
		},

		bson.M{"$sort":bson.M{
				"imgs_count_int":-1,
			},
		},
	})

	results_lst := []Stat__crawled_gifs{}
	err         := pipe.All(&results_lst)

	if err != nil {
		p_log_fun("ERROR",fmt.Sprint(err))
		return nil,err
	}

	end_time__unix_f := float64(time.Now().UnixNano())/1000000000.0

	//------------------
	var r interface{}
	r = results_lst
	create__stat_run("crawler_gifs",r,start_time__unix_f,end_time__unix_f,p_mongodb_coll,p_log_fun)
	//------------------

	return results_lst,nil
}
//-------------------------------------------------
func stats__crawled_images_domains(p_mongodb_coll *mgo.Collection,
								p_log_fun func(string,string)) ([]Stat__crawled_images_domain,error) {
	p_log_fun("FUN_ENTER","gf_crawl_stats__images.stats__crawled_images_domains()")



	start_time__unix_f := float64(time.Now().UnixNano())/1000000000.0

	pipe := p_mongodb_coll.Pipe([]bson.M{
		bson.M{"$match"  :bson.M{
				"t":"crawler_page_img",
			},
		},

		bson.M{"$project":bson.M{
				"id_str"              :true,
				"creation_unix_time_f":true,
				"cycle_run_id_str"    :true,
				"domain_str"          :true,
				"url_str"             :true,
				"origin_url_str"      :true, //page url from whos html this element was extracted
				"downloaded_bool"     :true,
				"valid_for_usage_bool":true,
				"s3_stored_bool"      :true,

				//"errors_num_i"        :bson.M{"$size":"$errors_lst",},
			},
		},

		bson.M{"$group":bson.M{
				"_id"                    :"$domain_str",
				//"_id"                    :bson.M{"domain_str":"$domain_str","cycle_run_id_str":"$cycle_run_id_str",},
				"imgs_count_int"         :bson.M{"$sum"     :1},
				"creation_unix_times_lst":bson.M{"$push"    :"$creation_unix_time_f"},
				"urls_lst"               :bson.M{"$push"    :"$url_str"},
				"origin_urls_lst"        :bson.M{"$addToSet":"$origin_url_str"},
				"downloaded_lst"         :bson.M{"$push"    :"$downloaded_bool"},
				"valid_for_usage_lst"    :bson.M{"$push"    :"$valid_for_usage_bool"},
				"s3_stored_lst"          :bson.M{"$push"    :"$s3_stored_bool"},
			},
		},

		/*bson.M{"$group":bson.M{
				"_id"           :"$_id.cycle_run_id_str",
				"imgs_count_int":bson.M{"$sum"     :1},
				""
			},
		},*/

		bson.M{"$sort":bson.M{
				"imgs_count_int":-1,
			},
		},
	})

	results_lst := []Stat__crawled_images_domain{}
	err         := pipe.All(&results_lst)

	if err != nil {
		p_log_fun("ERROR",fmt.Sprint(err))
		return nil,err
	}

	end_time__unix_f := float64(time.Now().UnixNano())/1000000000.0

	//------------------
	var r interface{}
	r = results_lst
	create__stat_run("crawler_images_domains",r,start_time__unix_f,end_time__unix_f,p_mongodb_coll,p_log_fun)
	//------------------

	return results_lst,nil
}