jQuery.fn.submitter = function() {
    this.each(function() {
        var that = $(this);
        that.click(function(ev) {
            ev.preventDefault();
            var form = $(that.attr('data-form'));
            form.attr('action',that.attr('href'));
            form.submit();
        })
    })
};