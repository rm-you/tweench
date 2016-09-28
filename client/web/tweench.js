var downloadLock = false;
var lastEvaluatedKey = null;
var docClient = new AWS.DynamoDB.DocumentClient();

function addImageToPage(image, post) {
    var url = base_path + image['path'];
    var thumb_url = base_thumb_path + image['path'];

    var colors = base_path + image['colors'];

    var li = document.createElement('li');
    li.classList.add('item');
    li.classList.add('hidden');

    var a = document.createElement('a');
    a.className = 'fancybox-thumb';
    a.href = url;
    a.rel = 'fancybox-thumb';
    a.alt = "";

    var pic = document.createElement('picture');
    pic.className = 'px300';

    var src = document.createElement('source');
    src.setAttribute('media', "(max-width: 300px)");
    src.setAttribute('srcset', url);

    var img = document.createElement('img');
    img.className = 'px300';
    img.src = thumb_url;
    img.alt = post.title;
    img.setAttribute('data-post', post.permalink);
    img.setAttribute('data-user', post.user);

    pic.appendChild(src);
    pic.appendChild(img);

    a.appendChild(pic);
    li.appendChild(a);
    $('#container').append(li);
    return li;
}

function tableQueryCallback(error, data) {
    console.log("Table query complete.");
    if (error) {
        console.log(error);
    } else {
        console.log(data);
        lastEvaluatedKey = data["LastEvaluatedKey"];
        var posts = data["Items"];
        var elements = [];
        for (var i = 0, posts_len = posts.length; i < posts_len; i++) {
            var post = posts[i];
            var images = post.images;
            if (typeof(images) === 'undefined') {
                continue;
            }
            for (var j = 0, images_len = images.length; j < images_len; j++) {
                if (typeof(images[j]['path']) !== 'undefined') {
                    elements.push(addImageToPage(images[j], post));
                }
            }
            if (elements.length >= maxImageCount) {
                lastEvaluatedKey.id = post.id;
                break;
            }
        }
        console.log("Loaded " + elements.length + " images.");
        var $container = $('#container');
        $container.imagesLoaded(function () {
            $container.masonry('appended', elements, true);
        });
    }
}

function layoutCompleteCallback(event, items) {
    console.log("Layout complete, enabling fancybox.");
    downloadLock = false;
    $(".hidden").removeClass("hidden");
    $(".fancybox-thumb").fancybox({
        padding: 0,
        margin: [20, 60, 20, 60],
        prevEffect: 'none',
        nextEffect: 'none',
        helpers: {
            title: {
                type: 'over'
            // },
            // thumbs: {
            //     height: 50
            }
        },
        beforeShow: function () {
            var alt = this.element.find('img').attr('alt');
            var post = this.element.find('img').attr('data-post');
            var user = this.element.find('img').attr('data-user');
            this.inner.find('img').attr('alt', alt);
            if (user && post)
                this.title = "<a style='color: white;' target='_blank' href='https://www.reddit.com/u/" + user + "/submitted/'>" + user + "</a> - <a style='color: white;' target='_blank' href=" + post + "'>" + alt + "</a>";
        },

        afterShow: function () {
            $(".fancybox-title").wrapInner('<div />').show();
            $(".fancybox-wrap").hover(function () {
                $(".fancybox-title").show();
            }, function () {
                $(".fancybox-title").hide();
            });
        }
    });
    if ($('#container')[0].children.length < minTotalImageCount) {
        getMoreImages(-1);
    }
}

function getMoreImages(page, sequence, scrollDirection) {
    if (downloadLock) {
        console.log("Already downloading images, aborting.");
        return;
    }
    if (lastEvaluatedKey === undefined) {
        // AWS docs claim LastEvaluatedKey will be null but really it is undefined
        console.log("Ran out of images. We're done!");
        return;
    } else if (lastEvaluatedKey === null) {
        // Set our initial key to undefined AFTER the null check
        lastEvaluatedKey = undefined;
    }

    downloadLock = true;
    if (sequence == null || sequence > 0) {
        console.log("Getting more images, page/direction: "
            + page + "/" + scrollDirection);
        var params = {
            TableName: "posts",
            IndexName: "subreddit-created-index",
            Limit: postLoadCount,
            KeyConditionExpression: "#sr = :name",
            ExpressionAttributeNames: {
                "#sr": "subreddit"
            },
            ExpressionAttributeValues: {
                ":name": subreddit
            },
            ExclusiveStartKey: lastEvaluatedKey,
            ScanIndexForward: false
        };
        docClient.query(params, tableQueryCallback);
    } else {
        console.log("Sequence was negative, ignoring.");
    }
}

function ceaseFireCallback() {
    return lastEvaluatedKey == null;
}
