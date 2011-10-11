/*
 * a jQuery plugin for listing tagged meetings from meetingtools
 *
 */

jQuery.fn.meetingtools = function(options) {
	
	var defaults = { 
		    onAdd:      function() {},
		    onUpdate:   function() {},
		    url:        'http://localhost:8000'
    }; 
	var options = $.extend({}, defaults, options); 
	
	this.each(function() {
		var tags = options.tags;
		var url = options.url;
		var url = options.url+'/room/+'+tags+'.json';
		var div = $(this);
		div.html(''); // stop any spinners;
		$.getJSON(url,function(data) {
			div.append("<ul class=\"meeting-list\">");
			$.each(data,function(i,room) {
				var html = "<li class=\"meeting\"><h4>"+room['name']+"</h4><div class=\"meeting-info\">";
				if (room['description']) {
					html += "<div class=\"meeting-description\">";
					html += room['description'];
					html += "</div>";
				}
				html += "<div class=\"meeting-participants\">" 
				html += "There are currently " + room['user_count'] + " participant(s) and " + room['host_count'] + " host(s) in the room.";
				html += "</div>";
				html += "<div class=\"meeting-button\"><a title=\"Enter "+room['name']+"\" href=\"" + room['url'] + "\">Enter " + room['name'] + "</a></div>";
				html += "<div class=\"meeting-url\">" + room['url'] + "</a></div>";
				html += "</div>";
				html += "</li>";
				div.append(html);
				options.onAdd();
			});
			div.append("</ul>");
			options.onUpdate();
		});
		
		
	});
}