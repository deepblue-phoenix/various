//README - functions for working with GIF files

package gf_images_lib

import (
    "fmt"
    "os"
    "image"
    "image/draw"
    "image/gif"
    "image/png"

    "github.com/fatih/color"
)
//--------------------------------------------------
func Gif__get_frames(p_file_src *string,
				p_frames_images_dir_path_str *string,
				p_log_fun                    func(string,string)) ([]*string,error) {
	p_log_fun("FUN_ENTER","gf_images_gif.Gif__get_frames()")

	cyan  := color.New(color.FgCyan).SprintFunc()
	black := color.New(color.FgBlack).Add(color.BgWhite).SprintFunc()

	p_log_fun("INFO","")
	p_log_fun("INFO",cyan("                          GIF")+" - "+cyan("GET_FRAMES"))
	p_log_fun("INFO","")
	p_log_fun("INFO",black(*p_file_src))


	file,err := os.Open(*p_file_src)
    if err != nil {
        return nil,err
    }

	//---------------------
	//IMPORTANT!! - gif.DecodeAll - can and will panic frequently, because a lot of the GIF images on the internet are somewhat broken
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("Error while decoding: %s", r)
        }
    }()

    gif,err := gif.DecodeAll(file)

    if err != nil {
        return nil,err
    }
    //---------------------

    img_width,img_height := get_gif_dimensions(gif)

    overpaint_image := image.NewRGBA(image.Rect(0,0,img_width,img_height))


    //draw first frame of the GIF to the canvas
    draw.Draw(overpaint_image,
    		overpaint_image.Bounds(),
    		gif.Image[0],
    		image.ZP,
    		draw.Src)


	new_files_names_lst := []*string{}

    //IMPORTANT!! - save GIF frames to .png files on local filesystem
    for i,frame_img := range gif.Image {
        draw.Draw(overpaint_image,
        		overpaint_image.Bounds(),
        		frame_img,
        		image.ZP,
        		draw.Over)


        //save current stack of frames, overwriting the existing file
        new_file_name_str := fmt.Sprintf("%s%d%s", "<some path>", i, ".png")
        file,err          := os.Create(new_file_name_str)
        if err != nil {
            return nil,err
        }

        err = png.Encode(file,overpaint_image)
        if err != nil {
            return nil,err
        }

        file.Close()


        new_files_names_lst = append(new_files_names_lst,&new_file_name_str)
    }

    return new_files_names_lst,nil
}
//--------------------------------------------------
func get_gif_dimensions(p_gif *gif.GIF) (x, y int) {

    var lowestX  int
    var lowestY  int
    var highestX int
    var highestY int

    for _, img := range p_gif.Image {
        if img.Rect.Min.X < lowestX {
            lowestX = img.Rect.Min.X
        }
        if img.Rect.Min.Y < lowestY {
            lowestY = img.Rect.Min.Y
        }
        if img.Rect.Max.X > highestX {
            highestX = img.Rect.Max.X
        }
        if img.Rect.Max.Y > highestY {
            highestY = img.Rect.Max.Y
        }
    }

    return highestX - lowestX, highestY - lowestY
}