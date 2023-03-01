//if Setup source of evidence form elements based on the parsing_mode  -->

document.getElementById("parsing_mode").onchange = function() {
    document.getElementById("zipped_div").hidden = true;
    document.getElementById("dir_div").hidden = true;
    document.getElementById("velo_div").hidden = true;
    document.getElementById("s3_div").hidden = true;

    if (this.value == "Local") {
        document.getElementById("dir_div").hidden = false;
    }
    else if (this.value == "Upload") {
        document.getElementById("zipped_div").hidden = false;
    }
    else if (this.value == "S3") {
        document.getElementById("s3_div").hidden = false;
    }
    else if (this.value == "Velo") {
        document.getElementById("velo_div").hidden = false;
    }
}

// when pass_check checked show pass_div-->

document.getElementById("pass_check").onchange = function() {
    if (this.checked) {
        document.getElementById("pass_div").hidden = false;
    }
    else {
        document.getElementById("pass_div").hidden = true;
    }
}





// if plaso checked show div_tag-->
document.getElementById("plaso").onchange = function() {
    if (this.checked) {
        document.getElementById("div_tag").hidden = false;
    }
    else {
        document.getElementById("div_tag").hidden = true;
    }
}




// if timelines_drop have selected first option unhide timeline_name_div -->

document.getElementById("timelines_drop").onchange = function() {
    //if first <option> in this element is selected show timeline_name_div
    //get first option from this
    var first_option = document.getElementById("timelines_drop").options[0];
    //if first option is selected
    if (this.value == first_option.value) {
        document.getElementById("timeline_name_div").hidden = false;
        //clear value of the object id timeline
        document.getElementById("timeline").value = "";
    }
    else {
        document.getElementById("timeline_name_div").hidden = true;
        // set value of the object id timeline to the value of the selected option
        document.getElementById("timeline").value = this.value;
    }
    
}


//if upload to existing sketch chosen disable sketch_new and sketch_desc-->

document.getElementById("existing").onchange = function() {
    if (this.value == "Yes") {
        document.getElementById("sketch_new_div").hidden = true;
        document.getElementById("sketch_desc_div").hidden = true;
        document.getElementById("sketch_id_drop_div").hidden = false;
    }
    else {
        document.getElementById("sketch_new_div").hidden = false;
        document.getElementById("sketch_desc_div").hidden = false;
        document.getElementById("sketch_id_drop_div").hidden = true;
    }
}

// When user selects option in radio input with id "sketch_id_from_ts" send get request to /get_timelines/<sketch_id> where <sketch_id> is 8

   

function get_timelines(sketch_id) {
    //prepare request
    console.log("GET-timelines")
    var request = new XMLHttpRequest();
    //var sketch_id = this.value;
    var url = "/get_timelines/" + sketch_id;
    request.open("GET", url, true);
    request.onload = function() {
        //get response
        var data = JSON.parse(this.response);
        //clear dropdown
        var dropdown = document.getElementById("timelines_drop");
        
        //delete all options beside first one
        while (dropdown.options.length > 1) {
            dropdown.remove(1);
        }

        var option;
        for (var i = 0; i < data.length; i++) {
            option = document.createElement('option');
            option.text = data[i].timeline_name;
            option.value = data[i].timeline_name;
            dropdown.add(option);
        }
    }
    request.send();

}

