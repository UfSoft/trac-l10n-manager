/*
 * JTip
 * By Cody Lindley (http://www.codylindley.com)
 * Under an Attribution, Share Alike License
 * JTip is built on top of the very light weight jquery library.
 */

(function($) {

    $.fn.jTip = function(params) {

        params = params || {};
        ajax_params = $.extend({}, $.fn.jTip.ajax_params, params.ajax)
        messages = $.extend({}, $.fn.jTip.messages, params.messages)
        op = $.extend({}, $.fn.jTip.defaults, params)

        return this.each( function() {

            console.log(this);

            if ( op.trigger == "hover" ) {
                $(this).bind("mouseover", function(e) {
                    e.preventDefault();
                    JT_show(this);
                    return false;
                });
                $(this).bind("mousemove", function(e) {
                    return false;
                });
                $(this).bind("mouseout", function(e) {
                    $('#'+op.did).remove();
                    return false;
                });
                if ( ! op.follow_tooltip ) {
                    $(this).click( function() { return false; } );
                };
            } else if ( op.trigger == "click" ) {
                $(this).bind("click", function() {
                    JT_show(this);
                    $(document).bind("click", function() {
                        $('#'+op.did).remove();
                    });
                    return false;
                });
            };
        });
    };


    $.fn.jTip.messages = {
        follow_tooltip: 'Follow Tooltip',
        ajax_error_message: 'Ajax request to server failed',
        error_title: 'ERROR'
    };
    $.fn.jTip.ajax_params = { type: 'GET', cache: false, dataType: 'html' };
    $.fn.jTip.defaults = {
        title_element: 'h2',
        width: 250,
        trigger: 'click', // click or hover
        did: 'JT', // Default ID
        follow_tooltip: false,
        ajax: $.fn.jTip.ajax_params,
        messages: $.fn.jTip.messages,
        type: 'GET', cache: false, dataType: 'html',

    };

    function JT_show(el){

        ajax_params.url = el.href;
        ajax_params.error = JT_show_ajax_error
        ajax_params.success = JT_insert_html

        // If there's already a tooltip open, first close it
        if ( $('#'+op.did).length >= 1 ) { $('#'+op.did).remove() };

        var de = document.documentElement;
        var w = self.innerWidth || (de&&de.clientWidth) || document.body.clientWidth;
        var hasArea = w - getAbsoluteLeft(el);
        var clickElementy = getAbsoluteTop(el) - 3; //set y position

        if ( op.follow_tooltip ) {
            $(el).bind("click", function() {
               window.location = el.href;
            });
            $(el).css('cursor', 'pointer');
        }

        show_on_left = hasArea>((op.width*1)+75) && true || false;
        title_div = "#"+op.did + (show_on_left && "_close_left" || "_close_right")

        function JT_insert_html(html) {
            $('#'+op.did+'_copy').html(html);
            title = $('#'+op.did+'_copy h2');
            if(show_on_left){
                if ( title ) { $('#'+op.did+'_close_left').html(title.html()) };
            } else {
                if ( title ) { $('#'+op.did+'_close_right').html(title.html()) };
            }
            if ( title ) {
                title.remove();
            }
            $(title_div).toggle();
            if ( op.follow_tooltip && op.trigger != 'hover' ) {
                $('#'+op.did).append(
                    '<div id="'+op.did+'_follow_tooltip">' +
                    '<a href="'+el.href+'">'+messages.follow_tooltip+'</a></p>'
                );
            }
        };

        function JT_show_ajax_error() {
            $(title_div).html(messages.error_title).toggle()
            $('#'+op.did+'_copy').html('<p>'+messages.ajax_error_message+'</p>')
        }

        if(show_on_left){
            $("body").append(
              "<div id='"+op.did+"' style='width:" + op.width*1 +"px'>" +
              "<div id='"+op.did+"_arrow_left'></div>" +
              "<div id='"+op.did+"_close_left'>&nbsp;</div>" +
              "<div id='"+op.did+"_copy'><div class='"+op.did+"_loader'><div></div></div>"); //right side
            $("#"+op.did+"_close_left").hide();
            var arrowOffset = el.offsetWidth + 11;
            var clickElementx = getAbsoluteLeft(el) + arrowOffset; //set x position
        } else {
            $("body").append(
                "<div id='"+op.did+"' style='width:" + op.width*1 + "px'>" +
                "<div id='"+op.did+"_arrow_right' style='left:" + ((op.width*1)+1) + "px'></div>" +
                "<div id='"+op.did+"_close_right'>&nbsp;</div>" +
                "<div id='"+op.did+"_copy'><div class='"+op.did+"_loader'><div></div></div>");//left side
            $("#"+op.did+"_close_right").hide();
            var clickElementx = getAbsoluteLeft(el) - ((op.width*1) + 15); //set x position
        }

        $('#'+op.did).css({left: clickElementx + "px", top: clickElementy + "px"});
        $('#'+op.did).show();

        $.ajax(ajax_params);
    }

    function getAbsoluteLeft(o) {
        // Get an object left position from the upper left viewport corner
        oLeft = o.offsetLeft            // Get left position from the parent object
        while(o.offsetParent!=null) {   // Parse the parent hierarchy up to the document element
            oParent = o.offsetParent    // Get parent object reference
            oLeft += oParent.offsetLeft // Add parent left position
            o = oParent
        }
        return oLeft
    }

    function getAbsoluteTop(o) {
        // Get an object top position from the upper left viewport corner
        oTop = o.offsetTop              // Get top position from the parent object
        while( o.offsetParent!=null ) { // Parse the parent hierarchy up to the document element
            oParent = o.offsetParent    // Get parent object reference
            oTop += oParent.offsetTop   // Add parent top position
            o = oParent
        }
        return oTop
    }

})(jQuery);
