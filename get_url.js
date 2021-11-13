/* 리뉴얼된 런어스에서는 실행 불가능합니다 */

// 기간 지난 강좌 영상 여는 소스

function make_frame () {

    if (document.getElementById('vod_viewer') != null) {
        return  // video already exists
    }

    cmid = ""
    for (i=0; i<document.body.classList.length; i++) {
        if (document.body.classList[i].split("-")[0]=="cmid") {
    	cmid = document.body.classList[i].split("-")[1]
        break;
        }
    }

    if (cmid != "") {

        vod_viewer = document.createElement('iframe')
        vod_viewer.setAttribute('src', "video_player_cdn.php?id="+cmid)
        vod_viewer.setAttribute('id', 'vod_viewer')
        vod_viewer.setAttribute('style', "position: absolute;width: 100%;height: 100%;top: 0;left: 0;")
        vod_viewer.setAttribute('allowfullscreen','')
        vod_viewer.setAttribute('scrolling','no')

        vod_div = document.createElement('div')
        vod_div.setAttribute('class','')
        vod_div.setAttribute('style', 'position: relative;padding-top: 56%;')
        vod_div.appendChild(vod_viewer)

        vod_wrap = document.createElement('div')
        vod_wrap.setAttribute('class','video-wrap')
        vod_wrap.setAttribute('style','max-width: 600')
        vod_wrap.appendChild(vod_div)

        content_area = document.getElementsByClassName('detail-contents-area')[0]
        content_area.removeChild(content_area.firstChild)
        content_area.appendChild(vod_wrap)
        return vod_viewer
    } else {
        alert('no cmid information. check again!')
        return
    }

}
make_frame()

/**********/

// 채플 타입 영상 링크 받는 소스

function getStreamFileLink () {

    function get_doc () {
        // iframe = document.getElementById('vod_viewer');
        iframe = document.getElementsByTagName('iframe')[0];
        if (iframe == null) {
            return
        }
        var iframedoc = iframe.document;
        if (iframe.contentDocument) {
            var iframedoc = iframe.contentDocument;
        } else if (iframe.contentWindow) {
            var iframedoc = iframe.contentWindow.document;
        }
        return iframedoc
    }

    var doc = get_doc()
    if (doc == null) {
        alert('video does not exist in document. check again!');
        return
    }

    var vod_type = location.href.split('/')[4]

    var script = doc.body.getElementsByTagName("script")[0]
    if (script == null) {
        alert('please try one more time!');
        return;
    }

    var s = script.textContent.split("videourl")[1].split("'")[1]
    var t = document.createElement("textarea");
    document.body.appendChild(t);
    t.value = s;
    t.select();
    document.execCommand('copy');
    document.body.removeChild(t);

    alert('copied link to clipboard.');
    return s;

}

getStreamFileLink()

/**********/


/*

playtime_update(5,0,duration,duration,0);
positionfrom=positionto=0;
evented=1;

*/


/*

document.querySelectorAll('video')[0].playbackRate = 16

*/
