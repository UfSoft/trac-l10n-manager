(function($){

    /*
     * Helper function to hijack the link request and make it through AJAX
     */
    $.fn.hijaxLinkRequest = function(params) {

        var options = {
            progress: false,
            output: null
        };

        var loading_element = '<div class="progress">&nbsp;</div>';

        var params = params || {};
        var op = $.extend(options, params);
        var messages = $.extend({}, $.fn.hijaxLinkRequest.messages, params.messages)

        return this.each( function() {
            // Make sure elements are hijax'ed only once
            if ( $.data(this, 'hijaxed') ) { return /* break out of each loop */ };
            // Mark element as hijaxed
            $.data(this, 'hijaxed', true);

            var output_element = op.output || findOutputDivParent(this);

            var insertHtml = function(data) {
                if ( op.progress ) { $.unblockUI(); };
                $(output_element).html(data).animate(
                    { opacity: 1.0 },
                    { queue: false, speed: "fast" }
                );
            };

            var insertAjaxError = function() {
                if ( op.progress ) { $.unblockUI(); };
                $(output_element).html(
                    "<em>"+ messages.ajaxError +"</em>").animate(
                        { opacity: 1.0 },
                        { queue: false, speed: "fast" }
                );
            };

            jQuery(this).bind("click", function() {
                $.removeData(this); // Clear this element out of jQ's data cache
                $(output_element).animate(
                   {opacity: 0.0},
                   { queue: false, speed: "fast" }
                );
                if ( op.progress ) { $.blockUI({ message: loading_element }); };
                $.ajax({
                    async: true,
                    url: this.href,
                    type: 'GET',
                    cache: false,
                    error: insertAjaxError,
                    success: insertHtml,
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

    $.fn.hijaxLinkRequest.messages = {
        ajaxError: "An error ocurred",
    };


    $.fn.HideShow = function() {
        return this.each( function() {
            var fieldset = this;
            if ( ! $(fieldset).is('fieldset') ) return; // Return if it's not a fieldset
            var legend = $('legend:first', fieldset);
            if ( $(legend).length < 1 ) return; // return if there's no legend
            var child_div = $('div:first', fieldset);
            if ( $(child_div).length < 1 ) return; // return if layout is not good
            $(child_div).hide();
            $(legend).append(
              ' (<a class="showhide" href="javascript:void(0);">show</a>)');
            $('a:first', legend).bind('click', function() {
              var link = this;
              if ( $(link).text() == 'show' ) {
                  $(child_div).slideDown('fast', function() {
                      $(link).fadeOut('fast', function() {
                          $(link).text('hide').fadeIn('fast')
                      });
                  });
              } else {
                  $(child_div).slideUp('fast', function() {
                      $(link).fadeOut('fast', function() {
                          $(link).text('show').fadeIn('fast')
                      });
                  });
              };
              return false;
            });
        });
    };

    $.fn.projectCatalogOptions = function (mainurl, output_div) {
        return this.each( function() {
            var insertError = function () {
                $(output_div).addClass('system-message').html(
                    "Failed to get catalog templates from server"
                );
            };

            var insertHtml = function(data) {
                $(output_div).removeClass('system-message').html(data);
            };

            $(this).change( function() {
                $.ajax({
                    url: mainurl + "?project_catalogs=" + $(this).val(),
                    error: insertError,
                    success: insertHtml
                });
            });
            $(this).change();
        });
    };

    function findOutputDivParent(elem) {
        var parent_output_div = elem;
        while ( $(parent_output_div).get(0).tagName != 'DIV' ) {
            parent_output_div = $(parent_output_div).parent().get(0);
        };
        return parent_output_div;
    };

})(jQuery);
