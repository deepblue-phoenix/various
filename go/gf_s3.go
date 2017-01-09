package gf_core

import (
	//"errors"
	"bytes"
	"fmt"
	"net/http"
	"os"
	//"os/user"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	//"github.com/aws/aws-sdk-go/aws/awserr"
	//"github.com/aws/aws-sdk-go/aws/awsutil"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/s3/s3manager"
	//"github.com/aws/aws-sdk-go/aws/client"
)

//AKIAIHKJLFRT3S6BE2UA
//CkpTlfar0dHOciHBEbchDVH/ZKPqyN/kC8WY4wcb
//---------------------------------------------------
func S3__init(p_log_fun func(string, string)) (*s3.S3, *s3manager.Uploader) {
	p_log_fun("FUN_ENTER", "gf_s3.S3__init()")

	//--------------
	// DO NOT PUT credentials in code for production usage!
	// see https://www.socketloop.com/tutorials/golang-setting-up-configure-aws-credentials-with-official-aws-sdk-go
	// on setting creds from environment or loading from file

	aws_access_key_id := "AKIAIHKJLFRT3S6BE2UA"
	aws_secret_access_key := "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"
	token := ""

	creds := credentials.NewStaticCredentials(aws_access_key_id, aws_secret_access_key, token)
	_, err := creds.Get()

	//usr,_    := user.Current()
	//home_dir := usr.HomeDir
	//creds    := credentials.NewSharedCredentials(fmt.Sprintf("%s/.aws/credentials",home_dir),"default")
	//_, err := creds.Get()

	if err != nil {
		p_log_fun("ERROR", "failed to connect to AWS S3")
		os.Exit(1)
	}
	//--------------

	config := &aws.Config{
		Region:           aws.String("us-east-1"), //west-2"),
		Endpoint:         aws.String("s3.amazonaws.com"),
		S3ForcePathStyle: aws.Bool(true), // <-- without these lines. All will fail! fork you aws!
		Credentials:      creds,
		//LogLevel        :0, // <-- feel free to crank it up
	}
	sess := session.New(config)

	s3_uploader := s3manager.NewUploader(sess)
	s3_client := s3.New(sess)
	return s3_client, s3_uploader
}

//---------------------------------------------------
func S3__upload_file(p_bucket_name_str *string,
	p_target_file__local_path_str string,
	p_target_file__s3_path_str string,
	p_s3_client *s3.S3,
	p_s3_uploader *s3manager.Uploader,
	p_log_fun func(string, string)) (*string, error) {
	p_log_fun("FUN_ENTER", "gf_s3.S3__upload_file()")
	p_log_fun("INFO", "p_bucket_name_str          - "+*p_bucket_name_str)
	p_log_fun("INFO", "p_target_file__s3_path_str - "+p_target_file__s3_path_str)

	/*resp,err := p_s3_client.GetBucketLocation(&s3.GetBucketLocationInput{
										Bucket: aws.String("gf--img"), //required
									})
	if err != nil {
		return nil,err
	}*/
	//-----------------
	file, err := os.Open(p_target_file__local_path_str)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	//-----------------

	file_info, _ := file.Stat()
	var size int64 = file_info.Size()

	buffer := make([]byte, size)

	// read file content to buffer
	file.Read(buffer)

	file_bytes := bytes.NewReader(buffer) // convert to io.ReadSeeker type
	file_type := http.DetectContentType(buffer)

	//Upload uploads an object to S3, intelligently buffering large files
	//into smaller chunks and sending them in parallel across multiple goroutines.
	result, s3_err := p_s3_uploader.Upload(&s3manager.UploadInput{
		ACL:         aws.String("public-read"),
		Bucket:      aws.String(*p_bucket_name_str),
		Key:         aws.String(p_target_file__s3_path_str),
		ContentType: aws.String(file_type),
		Body:        file_bytes,
	})

	if s3_err != nil {
		return nil, s3_err
	}

	r_str := fmt.Sprint(result)
	return &r_str, nil

	/*params := &s3.PutObjectInput{
		Bucket       :aws.String(p_bucket_name_str),          // required
		Key          :aws.String(p_target_file__s3_path_str), // required
		ACL          :aws.String("public-read"),
		Body         :file_bytes,
		ContentLength:aws.Int64(size),
		ContentType  :aws.String(file_type),
		Metadata     :map[string]*string{
		     "Key":aws.String("MetadataValue"), //required
		},
		// see more at http://godoc.org/github.com/aws/aws-sdk-go/service/s3#S3.PutObject
	}

	result,err := p_s3_client.PutObject(params)

	if err != nil {
		p_log_fun("ERROR","AWS ERROR >>>>>>>>>>>>>>>>>>>>>>>")
		p_log_fun("ERROR",fmt.Sprint(err))

		if awsErr, ok := err.(awserr.Error); ok {
			// Generic AWS Error with Code, Message, and original error (if any)
			fmt.Println(awsErr.Code(), awsErr.Message(), awsErr.OrigErr())

			if reqErr, ok := err.(awserr.RequestFailure); ok {
				// A service error occurred
				return nil,errors.New(fmt.Sprintf("code - %s, message - %s, status_code - %s, request_id - %s",
									reqErr.Code(),
									reqErr.Message(),
									reqErr.StatusCode(),
									reqErr.RequestID()))
			}
		} else {
			// This case should never be hit, the SDK should always return an
			// error which satisfies the awserr.Error interface.
			return nil,errors.New(fmt.Sprint(err))
		}
	}

	r_str := fmt.Sprint(result)
	return &r_str,nil*/
}
