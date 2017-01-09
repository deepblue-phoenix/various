//README - part of my crawler library for use by my applications

package gf_crawl_lib

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
	"os"
	"time"
	//"github.com/aws/aws-sdk-go/service/s3"
	//"github.com/aws/aws-sdk-go/service/s3/s3manager"
	"github.com/PuerkitoBio/goquery"
	"github.com/fatih/color"
	"github.com/koyachi/go-nude"

	"apps/gf_images_lib"
	"gf_core"
)

//--------------------------------------------------
type Crawler_page_img struct {
	Id                   bson.ObjectId `bson:"_id,omitempty"`
	Id_str               string        `bson:"id_str"`
	T_str                string        `bson:"t"` //"crawler_page_img"
	Creation_unix_time_f float64       `bson:"creation_unix_time_f"`
	Cycle_run_id_str     string        `bson:"cycle_run_id_str"`
	Img_ext_str          string        `bson:"img_ext_str"` //jpg|gif|png
	Url_str              string        `bson:"url_str"`
	Domain_str           string        `bson:"domain_str"`
	Origin_url_str       string        `bson:"origin_url_str"` //page url from whos html this element was extracted

	//IMPORTANT!! - this is unique for the image src encountered. this way the same data links are not entered in duplicates,
	//              and using the hash the DB can qucikly be checked for existence of record
	Hash_str string `bson:"hash_str"`

	//IMPORTANT!! - indicates if the image was fetched from the remote server,
	//              and has been stored on S3 and ready for usage by other services.
	Downloaded_bool bool `bson:"downloaded_bool"`

	//IMPORTANT!! - the usage was determined to be useful for internal applications,
	//              they're not page elements, or other small unimportant parts.
	//              if it is valid for usage then a gf_image for this image should be
	//              found in the db
	Valid_for_usage_bool bool   `bson:"valid_for_usage_bool"`
	S3_stored_bool       bool   `bson:"s3_stored_bool"` //if persisting to s3 succeeded
	Nsfv_bool            bool   `bson:"nsfv_bool"`      //NSFV (not safe for viewing/nudity) flag for the image
	Image_id_str         string `bson:"image_id_str"`   //id of the gf_image for this corresponding crawler_page_img

	//Error_type_str       string        `bson:"error_type_str,omitempty"`
	//Error_id_str         string        `bson:"error_id_str,omitempty"`
}

//IMPORTANT!! - reference to an image, on a particular page.
//              the same image, with the same Url_str can appear on multiple pages, and this
//              struct tracks that, one record per reference
type Crawler_page_img_ref struct {
	Id                   bson.ObjectId `bson:"_id,omitempty"`
	Id_str               string        `bson:"id_str"`
	T_str                string        `bson:"t"` //"crawler_page_img_ref"
	Creation_unix_time_f float64       `bson:"creation_unix_time_f"`
	Cycle_run_id_str     string        `bson:"cycle_run_id_str"     json:"cycle_run_id_str"`
	Url_str              string        `bson:"url_str"`

	Domain_str     string `bson:"domain_str"`
	Origin_url_str string `bson:"origin_url_str"` //page url from whos html this element was extracted

	//IMPORTANT!! - this is unique for the image src encountered. this way the same data links are not entered in duplicates,
	//              and using the hash the DB can qucikly be checked for existence of record
	Hash_str string `bson:"hash_str"`
}

//--------------------------------------------------
func images__get_in_page(p_url_fetch *Crawler_url_fetch,
	p_cycle_run_id_str *string,
	p_crawler_name_str *string,
	p_s3_bucket_name_str string,
	p_runtime *Crawler_runtime,
	p_log_fun func(string, string)) error {
	p_log_fun("FUN_ENTER", "gf_crawl_images.images__get_in_page()")

	//this is used temporarily to donwload images to, before upload to S3
	images_store_local_dir_path_str := "."

	cyan := color.New(color.FgCyan).SprintFunc()
	yellow := color.New(color.FgYellow).SprintFunc()
	blue := color.New(color.FgBlue).SprintFunc()

	p_log_fun("INFO", cyan(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ---------------------------------------"))
	p_log_fun("INFO", "IMAGES__GET_IN_PAGE - "+blue(p_url_fetch.Url_str))
	p_log_fun("INFO", cyan(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ---------------------------------------"))

	//------------------
	//STAGE - pull all page image links

	imgs_count_int := 0
	crawled_images_lst := []*Crawler_page_img{}
	crawled_images_refs_lst := []*Crawler_page_img_ref{}

	p_url_fetch.goquery_doc.Find("img").Each(func(p_i int, p_elem *goquery.Selection) {

		origin_url_str := p_url_fetch.Url_str
		img_src_str, _ := p_elem.Attr("src")

		img_ext_str, ok, err := gf_images_lib.Get_image_ext_from_url(&img_src_str,
			p_log_fun)
		if err != nil {
			p_log_fun("ERROR", fmt.Sprint(err))
			t := "images_in_page__get_img_extension__failed"
			m := "failed to get file extension of image with img_src - " + img_src_str
			create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img_src_str, p_crawler_name_str,
				p_runtime, p_log_fun)
			return
		}
		if !ok {
			p_log_fun("INFO", yellow("image doesnt have a valid image extension - encountered - ")+cyan(*img_ext_str))
			return
		}
		//------------------
		//DOMAIN

		domain_str, err := get_domain(&img_src_str,
			&origin_url_str,
			p_log_fun)
		if err != nil {
			p_log_fun("ERROR", fmt.Sprint(err))
			t := "images_in_page__get_domain__failed"
			m := "failed to get domain of image with img_src - " + img_src_str
			create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img_src_str, p_crawler_name_str,
				p_runtime, p_log_fun)
			return
		}
		//-------------
		//COMPLETE_A_HREF

		complete_img_src_str, err := complete_url(&img_src_str,
			domain_str,
			p_log_fun)
		if err != nil {
			p_log_fun("ERROR", fmt.Sprint(err))
			t := "complete_url__failed"
			m := "failed to complete_url of image with img_src - " + img_src_str
			create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img_src_str, p_crawler_name_str,
				p_runtime, p_log_fun)
			return
		}
		//------------------
		p_log_fun("INFO", ">>>>> "+cyan("img")+" -- "+yellow(*domain_str)+" ------ "+yellow(fmt.Sprint(*complete_img_src_str)))
		//------------------
		//CRAWLER_PAGE_IMG

		creation_unix_time_f := float64(time.Now().UnixNano()) / 1000000000.0
		id_str := fmt.Sprintf("crawler_page_img:%f", creation_unix_time_f)

		//HASH
		to_hash_str := *complete_img_src_str //one Crawler_page_img for a given page url, no matter on how many pages it is referenced by
		hash := md5.New()
		hash.Write([]byte(to_hash_str))
		hash_str := hex.EncodeToString(hash.Sum(nil))

		img := &Crawler_page_img{
			Id_str:               id_str,
			T_str:                "crawler_page_img",
			Creation_unix_time_f: creation_unix_time_f,
			Cycle_run_id_str:     *p_cycle_run_id_str,
			Img_ext_str:          *img_ext_str,
			Url_str:              *complete_img_src_str,
			Domain_str:           *domain_str,
			Origin_url_str:       origin_url_str,
			Hash_str:             hash_str,
			Downloaded_bool:      false,
			Valid_for_usage_bool: false, //all images are initially set as invalid for usage
			S3_stored_bool:       false,
		}
		//------------------
		//CRAWLER_PAGE_IMG_REF

		creation_unix_time_f = float64(time.Now().UnixNano()) / 1000000000.0
		ref_id_str := fmt.Sprintf("domain:%f", creation_unix_time_f)

		//HASH
		//IMPORTANT!! - one Crawler_page_img_ref per page img reference, so if the same image is linked on several pages
		//              each of those references will have a different hash_str and will created a new Crawler_page_img_ref
		to_hash_str = *complete_img_src_str + origin_url_str
		hash = md5.New()
		hash.Write([]byte(to_hash_str))
		hash_str = hex.EncodeToString(hash.Sum(nil))

		img_ref := &Crawler_page_img_ref{
			Id_str:               ref_id_str,
			T_str:                "crawler_page_img_ref",
			Creation_unix_time_f: creation_unix_time_f,
			Cycle_run_id_str:     *p_cycle_run_id_str,
			Url_str:              *complete_img_src_str,
			Domain_str:           *domain_str,
			Origin_url_str:       origin_url_str,
			Hash_str:             hash_str,
		}
		//------------------
		//GIF
		if *img_ext_str == "gif" {

			//IMPORTANT!! - all GIF images are valid_for_usage, regardless of size
			img.Valid_for_usage_bool = true
		}
		//------------------

		crawled_images_lst = append(crawled_images_lst, img)
		crawled_images_refs_lst = append(crawled_images_refs_lst, img_ref)
		imgs_count_int = imgs_count_int + 1
	})
	//------------------
	//STAGE - IMG/IMG_REF DB PERSISTING

	crawled_images_existed_lst := []*bool{}

	for i, img := range crawled_images_lst {
		img_existed_bool, err := image__db_create(img,
			p_runtime,
			p_log_fun)
		if err != nil {
			p_log_fun("ERROR", fmt.Sprint(err))
			t := "image_db_create__failed"
			m := "failed db creation of image with img_url_str - " + img.Url_str
			create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
				p_runtime, p_log_fun)
			return err
		}

		crawled_images_existed_lst = append(crawled_images_existed_lst, img_existed_bool)

		img_ref := crawled_images_refs_lst[i]
		err = image__db_create_ref(img_ref,
			p_runtime,
			p_log_fun)
		if err != nil {
			p_log_fun("ERROR", fmt.Sprint(err))
			t := "image_ref_db_create__failed"
			m := "failed db creation of image_ref with img_url_str - " + img.Url_str
			create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
				p_runtime, p_log_fun)
			return err
		}
	}
	//------------------
	//STAGE - download images - done in its own stage so that it happens as fast as possible,
	//                          since when users view a page in their browser the browser issues all requests
	//                          for all the images in the page immediatelly.
	local_images_file_paths_lst := []*string{}

	for i, img := range crawled_images_lst {
		img_existed_bool := crawled_images_existed_lst[i]

		//IMPORTANT!! - only donwload the image if it doesnt already exist in the DB
		if img_existed_bool != nil && !*img_existed_bool {

			start_time_f := float64(time.Now().UnixNano()) / 1000000000.0

			local_image_file_path_str, err := image__download(img,
				&images_store_local_dir_path_str,
				p_runtime.Mongodb_coll,
				p_log_fun)
			if err != nil {
				p_log_fun("ERROR", fmt.Sprint(err))
				t := "image_download__failed"
				m := "failed downloading of image with img_url_str - " + img.Url_str
				create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
					p_runtime, p_log_fun)

				local_images_file_paths_lst = append(local_images_file_paths_lst, nil)
				continue
			}

			end_time_f := float64(time.Now().UnixNano()) / 1000000000.0

			local_images_file_paths_lst = append(local_images_file_paths_lst, local_image_file_path_str)

			//-------------
			//SEND_EVENT
			if p_runtime.Events_ctx != nil {
				events_id_str := "crawler_events"
				event_type_str := "image_download__http_request__done"
				msg_str := "completed downloading an image over HTTP"
				data_map := map[string]interface{}{
					"img_url_str":  img.Url_str,
					"start_time_f": start_time_f,
					"end_time_f":   end_time_f,
				}

				gf_core.Events__send_event(events_id_str,
					event_type_str, //p_type_str
					msg_str,        //p_msg_str
					data_map,
					p_runtime.Events_ctx,
					p_log_fun)
			}
			//-------------
		} else {
			local_images_file_paths_lst = append(local_images_file_paths_lst, nil)
		}
	}
	//------------------
	//ASSERT
	if len(crawled_images_lst) != len(local_images_file_paths_lst) {
		err_msg_str := " >>>>>>>>. LENGHTS NOT THE SAME"

		fmt.Println(len(crawled_images_lst))
		fmt.Println(len(local_images_file_paths_lst))
		p_log_fun("ERROR", err_msg_str)
		panic(err_msg_str)
	}
	//------------------
	//STAGE - determine if image is NSFV (contains nudity)
	//FIX!! - check if the processing cost of large images is not lower then determening NSFV first on large images,
	//        and then processing (which is whats done now). perhaps processing all images and then taking the
	img_is_nsfv_lst := []*bool{}
	for i, local_image_file_path_str := range local_images_file_paths_lst {

		//IMPORTANT!! - if image downloading fails, or there is any other issue, local_image_file_path_str is
		//              stored in local_images_file_paths_lst list as a 'nil' value
		if local_image_file_path_str != nil {
			img := crawled_images_lst[i]

			var is_nsfv_bool *bool
			var err error

			//--------------
			//GIF
			if img.Img_ext_str == "gif" {

				is_nsfv_bool, err = image__is_nsfv__gif(local_image_file_path_str,
					&img.Url_str,
					p_log_fun)
				if err != nil {
					p_log_fun("ERROR", "failed to do nudity-detection/filtering in GIF - "+img.Url_str+" - "+fmt.Sprint(err))

					t := "gif_is_nsfv_test__failed"
					m := "failed nsfv testing of GIF with img_url_str - " + img.Url_str
					create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
						p_runtime, p_log_fun)

					img_is_nsfv_lst = append(img_is_nsfv_lst, nil)
					continue
				}
				//--------------
				//STATIC-IMAGE
			} else {

				//IMPORTANT!! - if image has nudity it is flagged as not valid
				is_nsfv_bool, err = image__is_nsfv(local_image_file_path_str,
					p_log_fun)
				if err != nil {
					p_log_fun("ERROR", "failed to do nudity-detection/filtering in image - "+img.Url_str+" - "+fmt.Sprint(err))

					t := "image_is_nsfv_test__failed"
					m := "failed nsfv testing of image with img_url_str - " + img.Url_str
					create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
						p_runtime, p_log_fun)

					img_is_nsfv_lst = append(img_is_nsfv_lst, nil)
					continue
				}
			}
			//--------------

			//IMPORTANT!! - if image is flagged as NSFV its flag in the DB is updated
			if is_nsfv_bool != nil && *is_nsfv_bool {
				err := image__mark_as_nsfv(img,
					p_runtime.Mongodb_coll,
					p_log_fun)
				if err != nil {

					t := "image_mark_as_nsfv__failed"
					m := "failed nsfv marking (in DB) of image with img_url_str - " + img.Url_str
					create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
						p_runtime, p_log_fun)

					img_is_nsfv_lst = append(img_is_nsfv_lst, nil)
					continue
				}
			}

			img_is_nsfv_lst = append(img_is_nsfv_lst, is_nsfv_bool)
		} else {
			img_is_nsfv_lst = append(img_is_nsfv_lst, nil)
		}
	}
	//------------------
	//STAGE - process images

	images_thumbs_lst := []*gf_images_lib.Image_thumbs{}
	for i, img := range crawled_images_lst {

		img_existed_bool := crawled_images_existed_lst[i]
		img_is_nsfv_bool := img_is_nsfv_lst[i]

		//check image has not already been processed (and is in the DB)
		//check image is not flagged as a NSFV image
		if (img_existed_bool != nil && !*img_existed_bool) && (img_is_nsfv_bool != nil && !*img_is_nsfv_bool) {

			local_image_file_path_str := local_images_file_paths_lst[i]
			image_thumbs, err := image__process(img,
				local_image_file_path_str,
				&images_store_local_dir_path_str,
				p_runtime.Mongodb_coll,
				p_log_fun)
			if err != nil {
				p_log_fun("ERROR", fmt.Sprint(err))
				t := "image_process__failed"
				m := "failed processing of image with img_url_str - " + img.Url_str
				create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
					p_runtime, p_log_fun)

				images_thumbs_lst = append(images_thumbs_lst, nil)
				continue
			}

			images_thumbs_lst = append(images_thumbs_lst, image_thumbs)
		} else {
			images_thumbs_lst = append(images_thumbs_lst, nil)
		}
	}
	//------------------
	//STAGE - S3 store the image

	for i, img := range crawled_images_lst {

		img_existed_bool := crawled_images_existed_lst[i]
		img_is_nsfv_bool := img_is_nsfv_lst[i]

		if (img_existed_bool != nil && !*img_existed_bool) && (img_is_nsfv_bool != nil && !*img_is_nsfv_bool) {
			//IMPORTANT!! - only store/persist if they are valid (of the right dimensions) or
			//              if they're a GIF (all GIF's are stored/persisted)
			if img.Img_ext_str == "gif" || img.Valid_for_usage_bool {
				local_image_file_path_str := local_images_file_paths_lst[i]
				image_thumbs := images_thumbs_lst[i]
				err := gf_images_lib.Trans__s3_store_image(local_image_file_path_str,
					image_thumbs,
					&p_s3_bucket_name_str,
					p_runtime.S3_client,
					p_runtime.S3_uploader,
					p_runtime.Mongodb_coll,
					p_log_fun)
				if err != nil {
					p_log_fun("ERROR", "failed up s3_store crawler_page_img document - "+fmt.Sprint(err))
					t := "image_s3_store__failed"
					m := "failed s3 storing of image with img_url_str - " + img.Url_str
					create_error_and_event(&t, &m, map[string]interface{}{"origin_page_url_str": p_url_fetch.Url_str}, &img.Url_str, p_crawler_name_str,
						p_runtime, p_log_fun)
					continue
				}

				//------------------
				img.S3_stored_bool = true
				err = p_runtime.Mongodb_coll.Update(bson.M{
					"t":        "crawler_page_img",
					"hash_str": img.Hash_str,
				},
					bson.M{
						"$set": bson.M{"s3_stored_bool": true},
					})
				if err != nil {
					p_log_fun("ERROR", "failed up update crawler_page_img document - s3_stored_bool field - "+fmt.Sprint(err))
					continue
				}
				//------------------
			}
		}
	}
	//------------------
	//STAGE - CLEANUP

	//IMPORTANT!! - delete local tmp transformed image, since the files
	//              have just been uploaded to S3 so no need for them localy anymore
	//              crawling servers are not meant to hold their own image files,
	//              and service runs in Docker with temporary
	for i, local_f_str := range local_images_file_paths_lst {

		if local_f_str != nil {
			image_thumbs := images_thumbs_lst[i]
			files_to_remove_lst := []string{
				*local_f_str,
			}

			//IMPORTANT!! - for images that are not valid (too small) or if they're GIF's, there are no
			//              thumbs that are created, and image_thumbs for those images is "nil"
			if image_thumbs != nil {
				files_to_remove_lst = append(files_to_remove_lst, image_thumbs.Small_local_file_path_str)
				files_to_remove_lst = append(files_to_remove_lst, image_thumbs.Medium_local_file_path_str)
				files_to_remove_lst = append(files_to_remove_lst, image_thumbs.Large_local_file_path_str)
			}

			for _, f_str := range files_to_remove_lst {
				err := os.Remove(f_str)
				if err != nil {
					p_log_fun("ERROR", "cant cleanup file - "+f_str)
					p_log_fun("ERROR", fmt.Sprint(err))
					panic(err)
				}
			}
		}
	}
	//------------------
	return nil
}

//--------------------------------------------------
func image__db_create(p_img *Crawler_page_img,
	p_runtime *Crawler_runtime,
	p_log_fun func(string, string)) (*bool, error) {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__db_create()")

	cyan := color.New(color.FgCyan).SprintFunc()
	yellow := color.New(color.FgYellow).SprintFunc()

	//------------
	//MASTER
	if p_runtime.Cluster_node_type_str == "master" {

		c, err := p_runtime.Mongodb_coll.Find(bson.M{
			"t":        "crawler_page_img",
			"hash_str": p_img.Hash_str,
		}).Count()
		if err != nil {
			return nil, err
		}

		//crawler_page_img already exists, from previous crawls, so ignore it
		var exists_bool bool
		if c > 0 {
			p_log_fun("INFO", yellow(">>>>>>>> - DB PAGE_IMAGE ALREADY EXISTS >-- ")+cyan(p_img.Url_str))

			exists_bool = true
			return &exists_bool, nil
		} else {

			//IMPORTANT!! - only insert the crawler_page_img if it doesnt exist in the DB already
			err = p_runtime.Mongodb_coll.Insert(p_img)
			if err != nil {
				p_log_fun("ERROR", fmt.Sprint(err))
				return nil, err
			}
			exists_bool = false
			return &exists_bool, nil
		}
	}
	//------------
	//WORKER
	if p_runtime.Cluster_node_type_str == "worker" {

	}
	//------------

	return nil, nil
}

//--------------------------------------------------
func image__db_create_ref(p_img_ref *Crawler_page_img_ref,
	p_runtime *Crawler_runtime,
	p_log_fun func(string, string)) error {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__db_create_ref()")

	if p_runtime.Cluster_node_type_str == "master" {

		c, err := p_runtime.Mongodb_coll.Find(bson.M{
			"t":        "crawler_page_img_ref",
			"hash_str": p_img_ref.Hash_str,
		}).Count()
		if err != nil {
			return err
		}

		//crawler_page_img already exists, from previous crawls, so ignore it
		if c > 0 {
			return nil
		} else {

			//IMPORTANT!! - only insert the crawler_page_img if it doesnt exist in the DB already
			err = p_runtime.Mongodb_coll.Insert(p_img_ref)
			if err != nil {
				p_log_fun("ERROR", fmt.Sprint(err))
				return err
			}
		}
	} else {

	}

	return nil
}

//--------------------------------------------------
func image__download(p_image *Crawler_page_img,
	p_images_store_local_dir_path_str *string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (*string, error) {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__download()")

	cyan := color.New(color.FgCyan).SprintFunc()
	yellow := color.New(color.FgYellow).SprintFunc()

	p_log_fun("INFO", cyan("       >>>>>>>>>>>>> ----------------------------- ")+yellow("DOWNLOAD_IMAGE"))

	local_image_file_path_str, err := gf_images_lib.Fetcher__get_extern_image(&p_image.Url_str,
		p_images_store_local_dir_path_str,

		//IMPORTANT!! - dont add any time delay, instead download images as fast as possible
		//              since they're all in the same page, and are expected to be downloaded
		//              by the users browser in rapid succession, so no need to simulate user delay
		false, //p_random_time_delay_bool
		p_mongodb_coll,
		p_log_fun)
	if err != nil {
		return nil, err
	}

	p_image.Downloaded_bool = true
	err = p_mongodb_coll.Update(bson.M{
		"t": "crawler_page_img",

		//IMPORTANT!! - search by "hash_str", not "id_str", because p_image's id_str might not
		//              be the id_str of the p_image (with the same hash_str) that was written to the DB.
		//              (it might be an old p_image from previous crawler runs. to conserve DB space the crawler
		//              system doesnt write duplicate crawler_page_img's to the DB.
		"hash_str": p_image.Hash_str,
	},
		bson.M{
			"$set": bson.M{"downloaded_bool": true},
		})
	if err != nil {
		return nil, err
	}

	return local_image_file_path_str, nil
}

//--------------------------------------------------
func image__process(p_image *Crawler_page_img,
	p_local_image_file_path_str *string,
	p_images_store_local_dir_path_str *string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (*gf_images_lib.Image_thumbs, error) {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__process()")

	cyan := color.New(color.FgCyan).SprintFunc()
	yellow := color.New(color.FgYellow).SprintFunc()

	p_log_fun("INFO", cyan("       >>>>>>>>>>>>> ----------------------------- ")+yellow("PROCESS_IMAGE"))

	//----------------------------
	//GIF
	if p_image.Img_ext_str == "gif" {
		return nil, nil
	} else {
		//----------------------------
		image_thumbs, err := image__process_regular(p_image,
			p_local_image_file_path_str,
			p_images_store_local_dir_path_str,
			p_mongodb_coll,
			p_log_fun)
		if err != nil {
			return nil, err
		}
		return image_thumbs, nil
	}
	//----------------------------
	return nil, nil
}

//--------------------------------------------------
func image__process_regular(p_image *Crawler_page_img,
	p_local_image_file_path_str *string,
	p_images_store_local_dir_path_str *string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) (*gf_images_lib.Image_thumbs, error) {
	p_log_fun("FUN_ENTER", "gf_crawl_images.image__process_regular()")

	//----------------------
	//CONFIG
	image_client_type_str := "gf_crawl_images"
	image_flow_name_str := "discovered"
	//----------------------

	cyan := color.New(color.FgCyan).SprintFunc()
	yellow := color.New(color.FgYellow).SprintFunc()

	//-------------------
	file, err := os.Open(*p_local_image_file_path_str)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	img_width_int, img_height_int, err := gf_images_lib.Get_image_dimensions(file,
		p_image.Url_str,
		p_log_fun)
	if err != nil {
		return nil, err
	}
	//-------------------

	//IMPORTANT!! - check that the image is too small, and is likely to be irrelevant
	//              part of a particular page
	if img_width_int <= 130 || img_height_int <= 130 {
		p_log_fun("INFO", yellow("IMG IS SMALLER THEN MINIMUM DIMENSIONS (width-"+cyan(fmt.Sprint(img_width_int))+"/height-"+cyan(fmt.Sprint(img_height_int))+")"))
		return nil, nil
	} else {

		//--------------------------------
		//TRANSFORM DOWNLOADED IMAGE - CREATE THUMBS, SAVE TO DB, AND UPLOAD TO AWS_S3

		gf_image_id_str, err := gf_images_lib.Image__create_id_from_url(&p_image.Url_str,
			p_log_fun)
		image_origin_url_str := p_image.Url_str
		image_origin_page_url_str := p_image.Origin_url_str
		images_store_thumbnails_local_dir_path_str := *p_images_store_local_dir_path_str

		t_output_map, err := gf_images_lib.Transform_image(gf_image_id_str,
			&image_client_type_str,
			&image_flow_name_str,
			&image_origin_url_str,
			&image_origin_page_url_str,
			p_local_image_file_path_str,
			&images_store_thumbnails_local_dir_path_str,

			//&images_s3_bucket_name_str,
			//p_s3_client,
			//p_s3_uploader,
			p_mongodb_coll,
			p_log_fun)
		if err != nil {
			p_log_fun("ERROR", "failed to transformed craled/fetched image - "+fmt.Sprint(err))
			return nil, err
		}

		image_thumbs := t_output_map["image_thumbs"].(*gf_images_lib.Image_thumbs)
		//-------------
		//DB
		p_image.Valid_for_usage_bool = true
		err = p_mongodb_coll.Update(bson.M{
			"t":      "crawler_page_img",
			"id_str": p_image.Id_str,
		},
			bson.M{"$set": bson.M{
				//IMPORTANT!! - gf_image has been created for this page_image, and so the appropriate
				//              image_id_str needs to be set in the page_image DB record
				"image_id_str": *gf_image_id_str,

				//IMPORTANT!! - image has been transformed, and is ready to be used further
				//              by other apps/services, either for display, or further calculation
				"valid_for_usage_bool": true,
			},
			})
		//-------------

		image__mark_as_valid_for_usage(p_image,
			*gf_image_id_str,
			p_mongodb_coll,
			p_log_fun)
		//--------------------------------

		return image_thumbs, nil
	}

	return nil, nil
}

//--------------------------------------------------
func image__mark_as_valid_for_usage(p_image *Crawler_page_img,
	p_gf_image_id_str string,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) error {
	p_log_fun("FUN_ENTER", "gf_crawl_images.image__mark_as_valid_for_usage()")

	p_image.Valid_for_usage_bool = true
	err := p_mongodb_coll.Update(bson.M{
		"t":      "crawler_page_img",
		"id_str": p_image.Id_str,
	},
		bson.M{"$set": bson.M{
			//IMPORTANT!! - gf_image has been created for this page_image, and so the appropriate
			//              image_id_str needs to be set in the page_image DB record
			"image_id_str": p_gf_image_id_str,

			//IMPORTANT!! - image has been transformed, and is ready to be used further
			//              by other apps/services, either for display, or further calculation
			"valid_for_usage_bool": true,
		},
		})
	return err
}

//--------------------------------------------------
func image__is_nsfv__gif(p_img_gif_path_str *string,
	p_img_gif_origin_url_str *string,
	p_log_fun func(string, string)) (*bool, error) {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__is_nsfv__gif()")

	cyan := color.New(color.FgCyan).SprintFunc()
	green := color.New(color.FgBlack).Add(color.BgGreen).SprintFunc()
	black := color.New(color.FgBlack).Add(color.BgWhite).SprintFunc()

	p_log_fun("INFO", green(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>------------------------------------------------"))
	p_log_fun("INFO", green(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>------------------------------------------------"))
	p_log_fun("INFO", "")
	p_log_fun("INFO", cyan("                          GIF")+" - "+cyan("GET_FRAMES"))
	p_log_fun("INFO", "")
	p_log_fun("INFO", black(*p_img_gif_origin_url_str))
	p_log_fun("INFO", green(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>------------------------------------------------"))
	p_log_fun("INFO", green(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>------------------------------------------------"))

	frames_images_dir_path_str := "./"
	new_files_names_lst, err := gf_images_lib.Gif__get_frames(p_img_gif_path_str,
		&frames_images_dir_path_str,
		p_log_fun)
	if err != nil {
		return nil, err
	}
	//-------------------------
	//CLEANUP!! - remove extracted GIF frames in dir frames_images_dir_path_str,
	//            after NSFV analysis is complete
	defer func() {
		for _, f_str := range new_files_names_lst {
			err := os.Remove(*f_str)
			if err != nil {

			}
		}
	}()
	//-------------------------
	//IMPORTANT!! - run NSFV detection on each GIF frame, and for the first one that fails the test
	//              use it as a signal to mark the whole GIF as NSFV
	for _, frame_image_file_path_str := range new_files_names_lst {
		is_nsfv_bool, err := image__is_nsfv(frame_image_file_path_str,
			p_log_fun)
		if err != nil {
			return nil, err
		}

		//-----------------
		//IMPORTANT!! - first frame that fails the NSFV test indicates the whole GIF is NSFV
		if is_nsfv_bool != nil && *is_nsfv_bool {
			return is_nsfv_bool, nil
		}
		//-----------------
	}
	//-------------------------

	is_nsfv_bool := false //if all frames pass as non-nsfv then the GIF is not NSFV
	return &is_nsfv_bool, err
}

//--------------------------------------------------
func image__is_nsfv(p_img_path_str *string,
	p_log_fun func(string, string)) (*bool, error) {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__is_nsfv()")

	is_nude_bool, err := nude.IsNude(*p_img_path_str)
	if err != nil {
		return nil, err
	}
	p_log_fun("INFO", "image is_nude - "+fmt.Sprint(is_nude_bool))
	return &is_nude_bool, nil
}

//--------------------------------------------------
func image__mark_as_nsfv(p_image *Crawler_page_img,
	p_mongodb_coll *mgo.Collection,
	p_log_fun func(string, string)) error {
	//p_log_fun("FUN_ENTER","gf_crawl_images.image__mark_as_nsfv()")

	err := p_mongodb_coll.Update(bson.M{
		"t":      "crawler_page_img",
		"id_str": p_image.Id_str,
	},
		bson.M{
			"$set": bson.M{"nsfv_bool": true},
		})
	if err != nil {
		return err
	}

	return nil
}
