# -*- coding: utf-8 -*-
import re, base64
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.parser import cParser
from resources.lib.util import cUtil
from resources.lib.cCFScrape import cCFScrape

SITE_IDENTIFIER = 'foxx_to'
SITE_NAME = 'Foxx'
SITE_ICON = 'foxx.png'

URL_MAIN = 'https://foxx.to/'
URL_FILME = URL_MAIN + 'film'
URL_SERIE = URL_MAIN + 'serie'
URL_SEARCH = URL_MAIN + '?s=%s'

QUALITY_ENUM = {'240p': 0, '360p': 1, '480p': 2, '720p': 3, '1080p': 4, '240': 0, '360': 1, '480': 2, '720': 3,
                '1080': 4}


def load():
    params = ParameterHandler()
    oGui = cGui()
    params.setParam('sUrl', URL_FILME)
    oGui.addFolder(cGuiElement('Filme', SITE_IDENTIFIER, 'showEntries'), params)
    oGui.addFolder(cGuiElement('Genres', SITE_IDENTIFIER, 'showGenres'), params)
    params.setParam('sUrl', URL_SERIE)
    oGui.addFolder(cGuiElement('Serien', SITE_IDENTIFIER, 'showEntries'), params)
    oGui.addFolder(cGuiElement('Suche', SITE_IDENTIFIER, 'showSearch'))
    oGui.setEndOfDirectory()


def showGenres():
    oGui = cGui()
    params = ParameterHandler()
    sHtmlContent = cRequestHandler(URL_MAIN).request()
    pattern = 'Filme</a><ul[^>]*class="sub-menu">.*?</ul></li><li[^>]*id'
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)

    if not isMatch:
        oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    pattern = '<a[^>]*href="([^"]+)".*?>([^"]+)</a>'
    isMatch, aResult = cParser.parse(sHtmlContainer, pattern)

    if not isMatch:
        oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    for sUrl, sName in aResult:
        sName = cUtil.cleanse_text(sName)
        params.setParam('sUrl', sUrl)
        oGui.addFolder(cGuiElement(sName.strip(), SITE_IDENTIFIER, 'showEntries'), params)
    oGui.setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    sHtmlContent = oRequest.request()
    pattern = '<div[^>]*class="poster"><img src="([^"]+)"[^>]alt="([^"]+).*?</div><a href="([^"]+).*?<span>([\d]+)</span>.*?<div[^>]class="texto">([^"]+)</div>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)

    if not isMatch:
        if not sGui: oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    cf_cookie = cCFScrape().createUrl(entryUrl, oRequest).replace(entryUrl, '')

    total = len(aResult)
    for sThumbnail, sName, sUrl, sYear, sDesc in aResult:
        sThumbnail = re.sub('-\d+x\d+\.', '.', sThumbnail)
        isTvshow = True if "serie" in sUrl else False
        if sThumbnail and not sThumbnail.startswith('http'):
            sThumbnail = URL_MAIN + sThumbnail

        sThumbnail += cf_cookie
        
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showSeasons' if isTvshow else 'showHosters')
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setFanart(sThumbnail)
        oGuiElement.setYear(sYear)
        oGuiElement.setDescription(sDesc)
        sUrl = cUtil.quotePlus(sUrl)
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        oGui.addFolder(oGuiElement, params, isTvshow, total)

    if not sGui:
        pattern = '"next"[^>]*href="([^"]+)'
        isMatchNextPage, sNextUrl = cParser.parseSingleResult(sHtmlContent, pattern)
        if isMatchNextPage:
            params.setParam('sUrl', sNextUrl)
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('tvshows' if 'serie' in sUrl else 'movies')
        oGui.setEndOfDirectory()


def showSeasons():
    oGui = cGui()
    params = ParameterHandler()
    sUrl = params.getValue('entryUrl')
    sThumbnail = params.getValue('sThumbnail')
    sTVShowTitle = params.getValue('sName')
    sHtmlContent = cRequestHandler(sUrl).request()
    pattern = '<span[^>]*class="se-t[^"]*"[^>]*>(\d+)</span>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)

    if not isMatch:
        oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    total = len(aResult)
    for sSeasonNr in aResult:
        oGuiElement = cGuiElement("Staffel " + sSeasonNr, SITE_IDENTIFIER, 'showEpisodes')
        oGuiElement.setMediaType('season')
        oGuiElement.setTVShowTitle(sTVShowTitle)
        oGuiElement.setSeason(sSeasonNr)
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setFanart(sThumbnail)
        params.setParam('sSeasonNr', int(sSeasonNr))
        oGui.addFolder(oGuiElement, params, True, total)
    oGui.setView('seasons')
    oGui.setEndOfDirectory()


def showEpisodes():
    oGui = cGui()
    params = ParameterHandler()
    sTVShowTitle = params.getValue('sName')
    entryUrl = params.getValue('entryUrl')
    sSeasonNr = params.getValue('sSeasonNr')
    sThumbnail = params.getValue('sThumbnail')
    sHtmlContent = cRequestHandler(entryUrl).request()
    pattern = '<span[^>]*class="se-t[^"]*">%s</span>.*?<ul[^>]*class="episodios"[^>]*>(.*?)</ul>' % sSeasonNr
    isMatch, sContainer = cParser.parseSingleResult(sHtmlContent, pattern)

    if not isMatch:
        oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    pattern = '<a[^>]*href="([^"]+)"[^>]*>([^<]+)'
    isMatch, aResult = cParser.parse(sContainer, pattern)

    if not isMatch:
        oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    total = len(aResult)
    for sUrl, sEpisodeNr in aResult:
        oGuiElement = cGuiElement(sEpisodeNr, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setTVShowTitle(sTVShowTitle)
        oGuiElement.setSeason(sSeasonNr)
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setFanart(sThumbnail)
        oGuiElement.setMediaType('episode')
        params.setParam('entryUrl', sUrl.strip())
        oGui.addFolder(oGuiElement, params, False, total)
    oGui.setView('episodes')
    oGui.setEndOfDirectory()


def showHosters():
    sUrl = ParameterHandler().getValue('entryUrl')
    sHtmlContent = cRequestHandler(sUrl).request()
    pattern = 'src="([^"]+)"[^>]*frameborder'
    isMatch, aResult = cParser().parse(sHtmlContent, pattern)
    hosters = []
    if not isMatch:
        return False
    
    for hUrl in aResult:
        if not hUrl.startswith('http'):
            hUrl = URL_MAIN[:-1] + hUrl
            
        oRequest = cRequestHandler(hUrl)
        oRequest.addHeaderEntry('Referer', hUrl)
        sHtmlContent = oRequest.request()

        if 'view.php' in hUrl:
            isMatch, sUrl = cParser().parseSingleResult(sHtmlContent, "jbdaskgs\s*=\s*'([^']+)'")
            if not isMatch: 
                continue

            sUrl = base64.b64decode(sUrl)
            isMatch, link = cParser.parseSingleResult(sUrl, 'file"\s*:\s*"([^"]+)"')
            if not isMatch: 
                continue

            hoster = {'link': link, 'name': 'Play'}
            hosters.append(hoster)
        elif 'watch.php' in hUrl:
            r = re.search('"label"\s*:\s*"([^"]+)",\s*"file"\s*:\s*"([^"]+)"', sHtmlContent)
            if not r:
                continue

            hoster = {'link': r.group(2), 'name': r.group(1)}
            hosters.append(hoster)
        elif 'wp-embed.php' in hUrl:
            isMatch, sUrl = cParser.parseSingleResult(sHtmlContent, '<iframe[^>]src="([^"]+)')
            if not isMatch:
                continue
            
	    isMatch, hname = cParser().parseSingleResult(sUrl, '^(?:https?://)?(?:[^@\n]+@)?([^:/\n]+)')
	    hoster = {'link': sUrl, 'name': hname}
	    hosters.append(hoster)
	    
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    if 'foxx' in sUrl:
        entryUrl = ParameterHandler().getValue('entryUrl')
        return [{'streamUrl': sUrl + '|Referer=' + entryUrl + '|User-Agent=Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0', 'resolved': True}]
    else:
        return [{'streamUrl': sUrl, 'resolved': False}]

def showSearchEntries(entryUrl=False, sGui=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl)
    sHtmlContent = oRequest.request()
    pattern = '2"><a[^>]href="([^"]+)"><img[^>]src="([^"]+)" alt="([^"]+).*?<span[^>]class="year">([\d]+)<.*?(?:<div[^>]class="contenido"><p>([^<]+)?)'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)

    if not isMatch:
        if not sGui: oGui.showInfo('xStream', 'Es wurde kein Eintrag gefunden')
        return

    cf_cookie = cCFScrape().createUrl(entryUrl, oRequest).replace(entryUrl, '')

    total = len(aResult)
    for sUrl,  sThumbnail, sName, sYear, sDesc in aResult:
        sThumbnail = re.sub('-\d+x\d+\.', '.', sThumbnail)
        if sThumbnail and not sThumbnail.startswith('http'):
            sThumbnail = URL_MAIN + sThumbnail

        sThumbnail += cf_cookie
        
        isTvshow = True if "serie" in sUrl else False
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showSeasons' if isTvshow else 'showHosters')
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setFanart(sThumbnail)
        oGuiElement.setYear(sYear)
        oGuiElement.setDescription(sDesc)
        sUrl = cUtil.quotePlus(sUrl)
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        oGui.addFolder(oGuiElement, params, isTvshow, total)

    if not sGui:
        pattern = "span[^>]*class=[^>]*current[^>]*>.*?</span><a[^>]*href='([^']+)"
        isMatchNextPage, sNextUrl = cParser.parseSingleResult(sHtmlContent, pattern)
        if isMatchNextPage:
            params.setParam('sUrl', sNextUrl)
            oGui.addNextPage(SITE_IDENTIFIER, 'showSearchEntries', params)
        oGui.setView('tvshows' if 'serie' in sUrl else 'movies')
        oGui.setEndOfDirectory()


def showSearch():
    oGui = cGui()
    sSearchText = oGui.showKeyBoard()
    if not sSearchText: return
    _search(False, sSearchText)
    oGui.setEndOfDirectory()


def _search(oGui, sSearchText):
    if not sSearchText: return
    showSearchEntries(URL_SEARCH % sSearchText.strip(), oGui)
