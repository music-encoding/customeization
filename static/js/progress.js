/**
 * Created by ahankins on 14-11-18.
 */

(function ($)
{
    var JobProgress = function (element, options)
    {
        /*
            These defaults are configurable at instantiation-time.
         */
        var defaults = {
            celeryJobId: null,
            interval: 1000,         // interval between progress calls in ms.
            progressObject: null    // the progress bar object.
        };

        var settings = $.extend({}, defaults, options);

        /*
            These values shouldn't be touched.
         */
        var globals = {
            refreshTimer: null
        };

        $.extend(settings, globals);

        var updateProgressBar = function (percentage)
        {
            settings.progressObject.css('width', percentage + '%');
        };

        /*
            When the Celery task is done, update the progress bar area with a download link.
         */
        var taskIsDone = function (data)
        {
            settings.progressObject.parent().fadeOut(500);
            var download = $("<div class=\"well\"><h4 style=\"text-align:center\"><a href=\"" + data.download + "\">Download Result</a></h4></div>")
            settings.parentSelector.append(download);
        };

        /*
            If the task failed, display a helpful message.
         */
        var taskHasFailed = function(status, error)
        {
            settings.progressObject.parent().fadeOut(500);
            var errorHeader = $("<div class=\"well\"><h4 style=\"text-align:center\">Error</h4>");
            var errorMsg = $("<p>The customization process failed with error " + error + ". Please report this error and " +
                "this message at <a href=\"https://github.com/music-encoding/customeization/issues\">https://github.com/music-encoding/customeization</a>." +
                "(status: " + status + ")</p>");
            settings.parentSelector.append(errorHeader);
            settings.parentSelector.append(errorMsg);
        };

        /*
            Periodically check the status of the job.
         */
        var progressQuery = function ()
        {
            $.ajax({
                url: '/progress/',
                data: {
                    "cid": settings.celeryJobId
                }
            })
            .always(function ()
            {
            })
            .done(function (data, status, xhr)
            {
                if (data.status === "SUCCESS")
                {
                    clearInterval(settings.refreshTimer);
                    updateProgressBar(data.percentage);
                    taskIsDone(data);
                }
                else
                {
                    updateProgressBar(data.percentage);
                }
            })
            .fail(function (xhr, status, error)
            {
                taskHasFailed(status, error);
                clearInterval(settings.refreshTimer);
            });
        };

        /*
            When this class is initialized, kick off a timer that
            periodically checks the progress of the job.
         */
        var init = function ()
        {
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
