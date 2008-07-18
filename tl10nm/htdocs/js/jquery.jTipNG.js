/*
 * JTip
 * By Cody Lindley (http://www.codylindley.com)
 * Under an Attribution, Share Alike License
 * JTip is built on top of the very light weight jquery library.
 */

(function($) {

    $.fn.jTipNG = function(params) {

        var params = params || {};
        var ajax_params = $.extend({}, $.fn.jTipNG.ajax_params, params.ajax);
        var messages = $.extend({}, $.fn.jTipNG.messages, params.messages);
        var op = $.extend({}, $.fn.jTipNG.defaults, params);

        function hideTooltip(elem) {
            $(elem).animate(
                {width: 0, height: 0}, {speed: 'fast', queue: false}).hide().remove();
        }

        return this.each( function() {
            var main_div_id = '#'+op.divIdPrefix;
            // Make sure elements are jTip'ed only once
            if ( $.data(this, 'jTipped') ) { return /* break out of each loop */ };
            // Mark element as hijaxed
            $.data(this, 'jTipped', true);

            if ( op.trigger == "hover" ) {
                $(this).bind("mouseover", function(e) {
                    blockEvents(e);
                    JT_show(this, op);
                    return false;
                });
                $(this).bind("mousemove", function(e) {
                    blockEvents(e);
                    return false;
                });
                $(this).bind("mouseout", function(e) {
                    blockEvents(e);
                    hideTooltip(main_div_id);
                    return false;
                });
                if ( ! op.follow_tooltip ) {
                    $(this).click( function() { return false; } );
                };
            } else if ( op.trigger == "click" ) {
                $(this).bind("click", function() {
                    JT_show(this, op);
                    $(document).bind("click", function() {
                        hideTooltip(main_div_id);
                    });
                    return false;
                });
            };
        });
    };


    $.fn.jTipNG.messages = {
        followTooltip: 'Follow Tooltip',
        ajaxErrorMessage: 'Ajax request to server failed',
        errorTitle: 'ERROR'
    };
    $.fn.jTipNG.ajax_params = { type: 'GET', cache: true,
                                dataType: 'html', async: true };
    $.fn.jTipNG.defaults = {
        titleElement: 'h2',   // Element on response to be used as tooltip title
        width: 300,           // Base tooltip width
        trigger: 'click',     // click or hover
        divIdPrefix: 'JT',    // Div ID prefix
        followTooltip: false, // Include link to follow the tooltips - for click trigger
        autoResize: true,     // Resize if content is bigger than default width
        ajax: $.fn.jTipNG.ajax_params,
        messages: $.fn.jTipNG.messages,
    };

    function JT_show(el, op){
        var ajax_params = op.ajax;
        var messages = op.messages;

        ajax_params.url = el.href + (el.href.indexOf('?')==-1 ? '?' : '&') + 'ajax_request=1';
        ajax_params.error = function() { JT_show_ajax_error(messages) };
        ajax_params.success = JT_insert_html;

        var de = document.documentElement;
        var w = self.innerWidth || (de&&de.clientWidth) || document.body.clientWidth;
        var hasArea = w - getAbsoluteLeft(el);
        var clickElementy = getAbsoluteTop(el) - 3; //set y position

        var show_on_right = hasArea>((op.width*1)+75) && true || false;
        var main_div_id = '#'+op.divIdPrefix;
        var title_div = "#"+op.divIdPrefix + (show_on_right && "_close_left" || "_close_right");
        var copy_div_id = '#'+op.divIdPrefix+'_copy';
        var arrow_div_id = "#"+op.divIdPrefix + (show_on_right && "_arrow_left" || "_arrow_right");


        if ( op.followTooltip && op.trigger == 'click' ) {
            $(el).bind("click", function() {
               window.location = el.href;
            });
            $(el).css('cursor', 'pointer');
        };


        function JT_insert_html(html) {
            $(copy_div_id).hide();
            $(copy_div_id).html(html);
            var title = $(op.titleElement, copy_div_id);
            if ( title ) { $(title_div).html(title.html()); title.remove(); };
            $(title_div).slideDown("fast");
            $(copy_div_id).slideDown("fast");
            if ( op.followTooltip && op.trigger != 'hover' ) {
                $(main_div_id).append(
                    '<div id="'+op.divIdPrefix+'_followTooltip">' +
                    '<a href="'+el.href+'">'+messages.followTooltip+'</a></p>'
                );
            };
            if ( op.autoResize ) {
                if ( op.trigger == 'hover') {
                    // With hover it seems that somethimes there's some
                    // resizing issues, we have to do this loop :\
                    var foo = false;
                    while ( !foo ) {
                       foo = resize();
                    };
                } else {
                    retval = resize();
                }
            };
        };

        function JT_show_ajax_error(messages) {
            $($(title_div).html(messages.errorTitle)).slideDown("fast")
            $(copy_div_id).html('<p>'+messages.ajaxErrorMessage+'</p>').slideDown("fast");
        };

        // If there's already a tooltip open, first close it
        if ( $(main_div_id).length >= 1 ) {
            $(main_div_id).animate(
               {width: 0, height: 0}, {speed: 'fast', queue: false}
            ).hide().remove();
        };

        if(show_on_right){
            $("body").append(
              "<div id='"+main_div_id.substring(1)+"' style='width:" + op.width*1 +"px'>" +
              "<div id='"+arrow_div_id.substring(1)+"'></div>" +
              "<div id='"+title_div.substring(1)+"'>&nbsp;</div>" +
              "<div id='"+copy_div_id.substring(1)+"'><div class='"+op.divIdPrefix+"_loader'><div></div></div>"); //right side
            var arrowOffset = el.offsetWidth + 11;
            var clickElementx = getAbsoluteLeft(el) + arrowOffset; //set x position
        } else {
            $("body").append(
                "<div id='"+main_div_id.substring(1)+"' style='width:" + op.width*1 + "px'>" +
                "<div id='"+arrow_div_id.substring(1)+"' style='left:" + ((op.width*1)+1) + "px'></div>" +
                "<div id='"+title_div.substring(1)+"'>&nbsp;</div>" +
                "<div id='"+copy_div_id.substring(1)+"'><div class='"+op.divIdPrefix+"_loader'><div></div></div>");//left side
            var clickElementx = getAbsoluteLeft(el) - ((op.width*1) + 15); //set x position
        };

        $(title_div).hide();
        $(main_div_id).css({left: clickElementx, top: clickElementy});
        $(main_div_id).show();
        $.ajax(ajax_params);

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
        };

        function resize() {
            var resize_value = 0;
            var widest_element;
            $(':visible', copy_div_id).each(function() {
                if ( this.offsetWidth == 0 ) {
                    return false;
                }
                // Grab element's overflow property
                var old_elem_overflow = $(this).css('overflow');
                // Set it to hiden so we can know how much of it's width was hidden
                $(this).css('overflow', 'hidden');
                if (  this.scrollWidth > this.offsetWidth ) {
                    // this.scrollWidth and this.offsetWidth do not match
                    // meaning that a portion was hidden.
                    var hidden_pixels = this.scrollWidth - this.offsetWidth;
                    if ( hidden_pixels > resize_value ) {
                        // new value is bigger than the older one, keep the new one
                        resize_value = hidden_pixels;
                        // Store widest element
                        widest_element = this;
                    };
                };
                // Restore overflow property
                $(this).css('overflow', old_elem_overflow);
            });
            if ( resize_value != 0 ) {
                // resize_value changed so, let's apply it
                var new_width = op.width*1+resize_value;
                if ( show_on_right ) {
                    if ( clickElementx + new_width > w ) {
                        // Won't fit screen
                        new_width -= new_width - (w - clickElementx - 40);
                        $(widest_element).css('overflow-x', 'scroll');
                        $(main_div_id).animate({'width': new_width}, 'fast');
                    } else {
                        $(main_div_id).animate({'width': new_width}, 'fast');
                    };
                } else {
                    var new_left = clickElementx - resize_value;
                    if ( new_left < 0 ) {
                        // Too Wide
                        $(widest_element).css('overflow-x', 'scroll');
                        new_width = new_width + new_left - 20;
                        new_left = 20;
                    }
                    $(main_div_id).animate(
                       {'left': new_left, 'width': new_width},
                       {duration: 'fast', queue: false}
                    );
                    $(arrow_div_id).animate(
                      {'left': new_width+1},
                      {duration: 'fast', queue: false}
                    );
                };
            }
            return true;
        };
    }

     function blockEvents(evt) {
         if ( evt.target ) {
             evt.preventDefault();
         } else {
             evt.returnValue = false;
         };
     };

})(jQuery);
