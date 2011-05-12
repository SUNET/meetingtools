/*
 *
 *
 *
 */

jQuery.fn.meetingtools = function(options) {
	
	this.each(function() {
		var tags = options.tags;
		var url = options.url;
		if (!url) {
			url = 'http://localhost:8000';
		}
		var url = url+'/room/+'+tags+'.json'
		var div = $(this)
		$.getJSON(url,function(data) {
			div.append("<ul style=\"list-style: none;\">")
			$.each(data,function(room) {
				div.append("<li style=\"display: list-item; list-style: none; padding: 2px; 5px;\" class=\"ui-helper-reset ui-widget ui-state-highlight ui-corner-all\">");
				div.append(room['url']);
				div.append("</li>");
			});
			div.append("</ul>")
		});
		
	});
}