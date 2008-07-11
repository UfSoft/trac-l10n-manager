(function($){
    /*
     * Helper function to hijack the form request and make it through AJAX
     */
    $.fn.hijax_vote_form = function() {
        return this.each( function() {
            console.log("Wrapping ", this);
            var url_array = this.action.split("/");
            var div_id = "#vote-" + url_array[url_array.length-1] + "-contents";

            function replace_html(data) {
                $(div_id).html(data).fadeIn("fast");
            };

            function insert_error() {
                $(div_id).append("<b>An error ocurred</b>");
            }

            jQuery(this).submit( function() {
                $(div_id).fadeOut("fast");
                $.ajax({
                    url: this.action,
                    type: 'POST',
                    cache: false,
                    error: insert_error,
                    success: replace_html,
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

})(jQuery);
