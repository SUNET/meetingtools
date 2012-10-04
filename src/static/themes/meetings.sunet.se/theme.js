
var is_ssl = ("https:" == document.location.protocol);
var asset_host = is_ssl ? "https://s3.amazonaws.com/getsatisfaction.com/" : "http://s3.amazonaws.com/getsatisfaction.com/";
document.write(unescape("%3Cscript src='" + asset_host + "javascripts/feedback-v2.js' type='text/javascript'%3E%3C/script%3E"));

var feedback_widget_options = {};

feedback_widget_options.display = "overlay";
feedback_widget_options.company = "sunet";
feedback_widget_options.placement = "right";
feedback_widget_options.color = "#222";
feedback_widget_options.style = "idea";
feedback_widget_options.product = "sunet_connect";

feedback_widget_options.limit = "3";

GSFN.feedback_widget.prototype.local_base_url = "http://getsatisfaction.com";
GSFN.feedback_widget.prototype.local_ssl_base_url = "https://getsatisfaction.com";

var feedback_widget = new GSFN.feedback_widget(feedback_widget_options);