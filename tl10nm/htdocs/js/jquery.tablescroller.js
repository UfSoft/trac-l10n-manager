/*
 * vim: sw=2 ts=2 fenc=utf-8
 *
 * TableScroller - Enable Scrolling on the table's TBODY, no more of those
 * long, long tables... At least for IE and Firefox, for now...
 *
 * Copyright (c) Pedro Algarvio (http://ufsoft.org)
 * Licensed under the BSD license.
 *
 * Version: 0.1
 *
 * - On Firefox the plugin's side-effect is that if you have a table with the
 *   'border-collapse' set to 'collapse', the plugin forces it to be
 *   'seperate'.
 *
 */
jQuery.tableScroller = {};
jQuery.tableScroller.settings = {ieDivNID: 0, scrollBarWidth: 0};

jQuery.fn.tableScroller = function(o) {
  var defaults = { minimumRows: 15 };
  //jQuery.tableScroller = {};
  //jQuery.tableScroller.settings = {info: 0};
  //console.log('INFO: ' + jQuery.tableScroller.settings.ieDivNID);

  return this.each( function() {
    /** merge default with custom options */
    jQuery.extend(defaults, o);

    /** Table object holder */
    table = this;
    //console.log('Running tableScroller for...');
    //console.log(table);

    if ( jQuery.browser.mozilla ) { mozScroll(); };
    if ( jQuery.browser.msie ) { ieScroll(); };

    function getScrollBarWidth() {
      /* Just a helper fucntion to get the scrollbar width acording to user settings */
      if ( jQuery.tableScroller.settings.scrollBarWidth != 0 ) {
        return jQuery.tableScroller.settings.scrollBarWidth;
      } else {
        var testDiv = jQuery('<div></div>').css(
          {position:"absolute", top:"-1000px", left:"-1000px", width:"100px", height:"100px", overflowY:"scroll"}
        ).appendTo(jQuery("body")).get(0);
        sbWidth = testDiv.offsetWidth - testDiv.clientWidth;
        jQuery(testDiv).remove();
        //console.log('Computed scrollbar width: ' + sbWidth);
        return sbWidth;
      };
    };

    function mozScroll() {
      //console.log('Running Mozilla Code');
      for ( i=0; i < table.tBodies.length; i++ ) {
        finalSetup = false;
        var rows = table.tBodies[i].rows;
        if ( rows.length > defaults.minimumRows ) {
          //console.log('We have the needed rows');
          finalSetup = true;
          jQuery(table.tBodies[i]).css(
            { overflowY: 'scroll', overflowX: 'hidden'/*, height: tbody_height */}
          );
          var lastChilds = jQuery(table.tBodies[i]).find('td:last-child');
          jQuery(lastChilds).css('padding-right', getScrollBarWidth() + 'px');
          var rows_height = jQuery(rows).height();
          //console.log('2nd: ' + jQuery('td', table.tBodies[i].rows[0]).css('height'));
          //console.log(table.tBodies[i].rows[0].cells)
          //console.log(table.tBodies[i].rows[0].cells[0].innerHTML);
          //console.log(jQuery(table.tBodies[i].rows[0].cells[0].innerHTML).css('height'));
          if ( rows_height == 0 ) {
            //console.log('Failed to get row height');
            rows_height = 32;  // We just need a number to set the div height
          };
          var tbody_height = (rows_height * defaults.minimumRows) + 'px';
          //console.log('Setting TBODY Height to: ' + tbody_height);
          jQuery(table.tBodies[i]).css(
            { /*overflow: 'auto', overflowX: 'hidden',*/ height: tbody_height }
          );
          if (finalSetup) { jQuery(table).css('borderCollapse', 'separate'); };
        };
      };
    }; // Ended mozScroll()

    function ieScroll() {
      //console.log('Running IE code');
      // temp var to sum up number of tbody rows in case there's more than on tbody
      var rows = 0;
      for ( i=0; i < table.tBodies.length; i++) {
        //console.log('TBODY['+i+'] has '+table.tBodies[i].rows.length+' rows');
        rows += table.tBodies[i].rows.length;
      };
      var tDivID = 'scrollWrapper-';
      //var scrollTop_ = 0;
      if ( rows > defaults.minimumRows ) {
        //console.log('We Have The Needed Rows: ' + rows);
        // Setup our Wrapper DIV
        divID = tDivID + jQuery.tableScroller.settings.ieDivNID;
        jQuery(table).wrap('<div id="' + divID + '"></div>');
        divObj = table.parentNode;
        jQuery(divObj).css({ width: '100%', overflowY: 'scroll', overflowX: 'hidden'});
        jQuery.tableScroller.settings.ieDivNID++;
        jQuery(table).css(
          //{ margin: '0px', marginRight: scrollBarWidth + 'px', top: '0px', left: '0px' }
          { margin: '0px', marginRight: getScrollBarWidth() + 'px', top: '0px', left: '0px' }
        );
        jQuery(table.tHead).css('position', 'relative');
        jQuery(table.tHead.rows).css(
          { top: '0px', bottom: '0px', position: 'relative' }
        );
        var rows_height = jQuery(table.tBodies[0].rows).height();
        if ( rows_height == 0 ) {
          //console.log('Failed to get row height');
          rows_height = 32; // We just need a number to set the div height
        };
        //console.log('Rows Height: ' + rows_height + ' MinRows: ' + defaults.minimumRows);
        var div_height = (rows_height * defaults.minimumRows) + 'px';
        //console.log('Setting  DIV Height to: ' + div_height);
        //jQuery('#'+divID).css(
        jQuery(divObj).css(
          { /*width: '100%', overflow: 'auto', overflowX: 'hidden',*/ height: div_height }
        );
        //var div_width = jQuery('#'+divID).width();
        var div_width = jQuery(divObj).width();
        var table_width = (div_width-getScrollBarWidth())*100/div_width;
        //console.log('DIV Width: '+div_width+'px; Table Width: '+table_width+'%');
        jQuery(table).css('width', table_width+'%');
        //console.log('Real Div Height: ' + jQuery('#'+divID).height());
        //console.log('2 INFO: ' + jQuery.tableScroller.settings.info);
        if ( table.onresort ) { // Table Has tableSorter Enabled
          jQuery("th", table.tHead.rows).click(
            function() { jQuery(table.tHead.rows).css('top', divObj.scrollTop + 'px'); }
          );
        };
      };
    }; // Ended ieScroll()

    function fixPosition() {
      div = table.parentNode;
      scrollTop_ = div.scrollTop;
      jQuerytable
    }; // Ended fixPosition()
  }); // Ended .each()
}; // Ended jQuery.fn.tableScroller




