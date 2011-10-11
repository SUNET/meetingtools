/*
 * a jQuery plugin for listing tagged meetings from meetingtools
 *
 */

jQuery.fn.meetingtools = function(options) {
	
	this.each(function() {
		var tags = options.tags;
		var url = options.url;
		if (!url) {
			url = 'http://localhost:8000';
		}
		var url = url+'/room/+'+tags+'.json';
		var div = $(this);
		$.getJSON(url,function(data) {
			html = "<ul class=\"meeting-list\">";
			$.each(data,function(i,room) {
				html += "<li class=\"meeting\"><h4>"+room['name']+"</h4><div class=\"meeting-info\">";
				if (room['description']) {
					html += "<div class=\"meeting-description\">";
					html += room['description'];
					html += "</div>";
				}
				html += "<div class=\"meeting-participants\">" 
				html += "There are currently " + room['user_count'] + " participant(s) and " + room['host_count'] + " host(s) in the room.";
				html += "</div>";
				html += "<div class=\"meeting-url\"><a href=\"" + room['url'] + "\">" + room['url'] + "</a></div>";
				html += "</div>";
				html += "</li>";
			});
			html += "</ul>";
			div.html(html);
		});
		
		
	});
}