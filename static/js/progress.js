/**
 * Created by ahankins on 14-11-18.
 */

(function ($)
{
    var JobProgress = function (element, options)
    {
        var defaults = {
            celeryJobId: null,
            interval: 1000,         // interval between progress calls in ms.
            progressObject: null    // the progress bar object.
        };

        var settings = $.extend({}, defaults, options);

        var globals = {
            refreshTimer: null
        };

        $.extend(settings, globals);

        var updateProgressBar = function (percentage)
        {
            settings.progressObject.css('width', percentage + '%');
        };

        var taskIsDone = function (data)
        {
            settings.progressObject.parent().fadeOut(500);
            var download = $("<div class=\"well\"><h4 style=\"text-align:center\"><a href=\"" + data.download + "\">Download Result</a></h4></div>")
            settings.parentSelector.append(download);
        };

        var taskHasFailed = function (data)
        {

        };

        var progressQuery = function ()
        {
            console.log('progress query called');

            $.ajax({
                url: '/progress/',
                data: {
                    "cid": settings.celeryJobId
                }
            })
            .always(function ()
            {
                console.log('request completed');
            })
            .done(function (data, status, xhr)
            {
                console.log('success');

                console.log(data.status);

                if (data.status === "SUCCESS")
                {
                    clearInterval(settings.refreshTimer);
                    updateProgressBar(data.percentage);
                    taskIsDone(data);
                    console.log(data)
                }
                else
                {
                    updateProgressBar(data.percentage);
                }
            })
            .fail(function (xhr, status, error)
            {
                console.error('fail');
                console.log(xhr);
                clearInterval(settings.refreshTimer);
            });
        };

        var init = function ()
        {
            console.log('Initializing with celery job id ' + settings.celeryJobId);
            settings.progressObject.css('width', '0%');
            settings.refreshTimer = setInterval(progressQuery, settings.interval);
        };

        init();

    };

    $.fn.job_progress = function (options)
    {
        return this.each(function ()
        {
            var element = $(this);
            if (element.data('job_progress'))
                return;

            options.parentSelector = element;

            var job_progress = new JobProgress(this, options);
            element.data('job_progress', job_progress);
        });
    }

})(jQuery);
