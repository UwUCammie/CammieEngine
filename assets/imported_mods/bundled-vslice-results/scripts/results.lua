debugMode = false
sicks = 0
goods = 0
bads  = 0
shits = 0
misses = 0
songNotes = 0
fullSongNotes = 0
accText = 0
maxCombo = 0
vAcc = 0
resultsOver = false
songOver = false
accuracyStyle = nil
highScore = callMethodFromClass("backend.Highscore", "getScore", {songName, difficulty})
themeR = getModSetting('customRed', 'V-Slice Results Screen')
themeG = getModSetting('customGreen', 'V-Slice Results Screen')
themeB = getModSetting('customBlue', 'V-Slice Results Screen')

function onCreate()
    if debugMode then
        setProperty('skipCountdown', true)
        luaDebugMode = true
    end
    if getModSetting('mobileHelp', 'V-Slice Results Screen') == 'Exit Button' then
        setPropertyFromClass('flixel.FlxG', 'mouse.visible', true)
    end
    nameSong = songName
    nameSong = string.gsub(nameSong, "[^%a%d]", " ")
    nameSong = string.gsub(nameSong, "%s+", " ")
    nameSong = string.gsub(nameSong, "^%s*(.-)%s*$", "%1")
    naughtyness = getModSetting('naughtyness', 'V-Slice Results Screen')
    themeColor = getModSetting('themeColor', 'V-Slice Results Screen')
    if getModSetting('accuracyStyle', 'V-Slice Results Screen') then
        accuracyStyle = 'vslice'
    else
        accuracyStyle = 'psych'
    end
    if themeColor == 'Red' then
        color = 0xfc495c
        colorB = 0xfd6a75
        colorD = 0xce1532
    elseif themeColor == 'Orange' then
        color = 0xff9940
        colorB = 0xfdc16a
        colorD = 0xdf5117
    elseif themeColor == 'Yellow' then
        color = 0xffdd30
        colorB = 0xffef63
        colorD = 0xe3a600
    elseif themeColor == 'Green' then
        color = 0x37e660
        colorB = 0x74fd6a
        colorD = 0x2e9a35
    elseif themeColor == 'Blue' then
        color = 0x4069ff
        colorB = 0x6b8ffe
        colorD = 0x291ed0
    elseif themeColor == 'Purple' then
        color = 0xce6cff
        colorB = 0xe18cff
        colorD = 0x8763f6
    elseif themeColor == 'Default' then
        color = 0xfec85c
    elseif themeColor == 'Custom' then
        color = rgbToHex(themeR, themeG, themeB)
        colorB = rgbToHex(themeR + 40, themeG + 40, themeB + 40)
        colorD = rgbToHex(themeR - 40, themeG - 40, themeB - 40)
    end
    if getModSetting('resultsChar', 'V-Slice Results Screen') == 'Adaptive' then
        if string.find(string.lower(getProperty('boyfriend.curCharacter')), 'bf') or string.find(string.lower(getProperty('boyfriend.curCharacter')), 'boyfriend') then
            char = 'bf'
        elseif string.find(string.lower(getProperty('boyfriend.curCharacter')), 'pico') then
            char = 'pico'
        else
            math.randomseed(os.time())
            randomChar = math.random(1, 2)
            if randomChar == 1 then
                char = 'bf'
            elseif randomChar == 2 then
                char = 'pico'
            end
        end
    elseif getModSetting('resultsChar', 'V-Slice Results Screen') == 'BF Only' then
        char = 'bf'
    elseif getModSetting('resultsChar', 'V-Slice Results Screen') == 'Pico Only' then
        char = 'pico'
    end
end

function onEndSong()
    if not resultsOver then
        math.randomseed(os.time())

        score = getProperty('songScore')
        scoreStr = tostring(score)
        notesStr = tostring(songNotes)
        sicksStr = tostring(sicks)
        goodsStr = tostring(goods)
        badsStr = tostring(bads)
        shitsStr = tostring(shits)
        missesStr = tostring(getProperty('songMisses'))
        if accuracyStyle == 'vslice' then
            accuracyNum = math.floor(vsliceAccuracyCalc(fullSongNotes, sicks or 0, goods or 0, bads or 0, shits or 0))
        elseif accuracyStyle == 'psych' then
            accuracyNum = math.floor(getProperty('ratingPercent') * 100)
        end
        accuracyStr = tostring(accuracyNum)

        if themeColor == 'Adaptive' then
            if (accuracyNum == 100) and (sicks == fullSongNotes) then --gold p rank
                color = 0xffcc54
                colorB = 0xffdf75
                colorD = 0xe3a136
            elseif (accuracyNum == 100) and (sicks < fullSongNotes) then --p rank
                color = 0xff5ce7
                colorB = 0xff85ed
                colorD = 0xb52186
            elseif accuracyNum > 89 and accuracyNum < 100 then --e rank
                color = 0xffee54
                colorB = 0xfff280
                colorD = 0xe0b12d
            elseif accuracyNum > 79 and accuracyNum < 90 then --silver g rank
                color = 0xd7e4fc
                colorB = 0xf7faff
                colorD = 0x4b5566
            elseif accuracyNum > 59 and accuracyNum < 80 then --bronze g rank
                color = 0xde7b35
                colorB = 0xfc9968
                colorD = 0x66290a
            elseif accuracyNum < 60 then --l rank
                color = 0x6449fc
                colorB = 0x6966ff
                colorD = 0x5429c2
            end
        end

            --<--RESULTS SCREEN OBJECTS-->--
        makeLuaSprite('superCoolResultsScreenBackground', '', -10, -10)
        makeGraphic('superCoolResultsScreenBackground', 1300, 740, 'FFFFFF')
        setProperty('superCoolResultsScreenBackground.color', color)
        setObjectCamera('superCoolResultsScreenBackground', 'other')
        setProperty('superCoolResultsScreenBackground.alpha', 0)
        addLuaSprite('superCoolResultsScreenBackground', true)

        makeLuaSprite('superCoolResultsScreenBackgroundFlash', '', -10, -10)
        makeGraphic('superCoolResultsScreenBackgroundFlash', 1300, 740, 'FFFFFF')
        setObjectCamera('superCoolResultsScreenBackgroundFlash', 'other')
        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0)
        addLuaSprite('superCoolResultsScreenBackgroundFlash', true)

        if string.lower(difficultyName) == 'easy' or string.lower(difficultyName) == 'normal' or string.lower(difficultyName) == 'hard' or string.lower(difficultyName) == 'erect' then
            makeLuaSprite('difficultyTextRS', 'diff_'..string.lower(difficultyName), 550, 0)
        elseif string.lower(difficultyName) == 'nightmare' then
            nightmare = true
            makeLuaSprite('difficultyTextRS', 'diff_'..string.lower(difficultyName), 550, 0)
        else
            makeLuaSprite('difficultyTextRS', 'diff_unknown', 550, 0)
        end
        setObjectCamera('difficultyTextRS', 'other')
        setProperty('difficultyTextRS.alpha', 0)

        makeLuaSprite('cpText', 'clearPercent/clearPercentText', 840, 285)
        setObjectCamera('cpText', 'other')
        setProperty('cpText.alpha', 0)
        addLuaSprite('cpText', true)

        makeAnimatedLuaSprite('cp1', 'clearPercent/clearPercentNumberLeft', 765, 362)
        addAnimationByPrefix('cp1', '1', 'number 1', 24, false)
        setObjectCamera('cp1', 'other')
        setProperty('cp1.alpha', 0)
        addLuaSprite('cp1', true)

        makeAnimatedLuaSprite('cp1W', 'clearPercent/clearPercentNumberLeftWhite', 765, 362)
        addAnimationByPrefix('cp1W', '1', 'number 1', 24, false)
        setObjectCamera('cp1W', 'other')
        setProperty('cp1W.alpha', 0)
        addLuaSprite('cp1W', true)

        makeAnimatedLuaSprite('cpL', 'clearPercent/clearPercentNumberLeft', 835, 358)
        addAnimationByPrefix('cpL', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpL', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpL', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpL', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpL', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpL', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpL', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpL', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpL', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpL', '9', 'number 9', 24, false)
        setObjectCamera('cpL', 'other')
        setProperty('cpL.alpha', 0)
        addLuaSprite('cpL', true)

        makeAnimatedLuaSprite('cpLW', 'clearPercent/clearPercentNumberLeftWhite', 835, 358)
        addAnimationByPrefix('cpLW', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpLW', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpLW', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpLW', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpLW', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpLW', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpLW', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpLW', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpLW', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpLW', '9', 'number 9', 24, false)
        setObjectCamera('cpLW', 'other')
        setProperty('cpLW.alpha', 0)
        addLuaSprite('cpLW', true)

        makeAnimatedLuaSprite('cpR', 'clearPercent/clearPercentNumberRight', 915, 358)
        addAnimationByPrefix('cpR', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpR', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpR', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpR', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpR', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpR', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpR', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpR', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpR', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpR', '9', 'number 9', 24, false)
        setObjectCamera('cpR', 'other')
        setProperty('cpR.alpha', 0)
        addLuaSprite('cpR', true)

        makeAnimatedLuaSprite('cpRW', 'clearPercent/clearPercentNumberRightWhite', 915, 358)
        addAnimationByPrefix('cpRW', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpRW', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpRW', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpRW', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpRW', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpRW', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpRW', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpRW', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpRW', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpRW', '9', 'number 9', 24, false)
        setObjectCamera('cpRW', 'other')
        setProperty('cpRW.alpha', 0)
        addLuaSprite('cpRW', true)

        makeAnimatedLuaSprite('cp1S', 'clearPercent/clearPercentNumberSmall', 559 + getProperty('difficultyTextRS.width'), 125 - 4)
        addAnimationByPrefix('cp1S', '1', 'number 1', 24, false)
        setObjectCamera('cp1S', 'other')
        setProperty('cp1S.alpha', 0)
        addLuaSprite('cp1S', true)

        makeAnimatedLuaSprite('cp1SW', 'clearPercent/clearPercentNumberSmallWhite', 559 + getProperty('difficultyTextRS.width'), 125 - 4)
        addAnimationByPrefix('cp1SW', '1', 'number 1', 24, false)
        setObjectCamera('cp1SW', 'other')
        setProperty('cp1SW.alpha', 0)
        addLuaSprite('cp1SW', true)

        makeAnimatedLuaSprite('cpSL', 'clearPercent/clearPercentNumberSmall', 592 + getProperty('difficultyTextRS.width'), 125 - 7)
        addAnimationByPrefix('cpSL', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpSL', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpSL', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpSL', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpSL', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpSL', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpSL', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpSL', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpSL', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpSL', '9', 'number 9', 24, false)
        setObjectCamera('cpSL', 'other')
        setProperty('cpSL.alpha', 0)
        addLuaSprite('cpSL', true)

        makeAnimatedLuaSprite('cpSLW', 'clearPercent/clearPercentNumberSmallWhite', 592 + getProperty('difficultyTextRS.width'), 125 - 7)
        addAnimationByPrefix('cpSLW', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpSLW', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpSLW', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpSLW', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpSLW', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpSLW', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpSLW', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpSLW', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpSLW', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpSLW', '9', 'number 9', 24, false)
        setObjectCamera('cpSLW', 'other')
        setProperty('cpSLW.alpha', 0)
        addLuaSprite('cpSLW', true)

        makeAnimatedLuaSprite('cpSR', 'clearPercent/clearPercentNumberSmall', 625 + getProperty('difficultyTextRS.width'), 125 - 10)
        addAnimationByPrefix('cpSR', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpSR', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpSR', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpSR', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpSR', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpSR', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpSR', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpSR', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpSR', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpSR', '9', 'number 9', 24, false)
        setObjectCamera('cpSR', 'other')
        setProperty('cpSR.alpha', 0)
        addLuaSprite('cpSR', true)

        makeAnimatedLuaSprite('cpSRW', 'clearPercent/clearPercentNumberSmallWhite', 625 + getProperty('difficultyTextRS.width'), 125 - 10)
        addAnimationByPrefix('cpSRW', '0', 'number 0', 24, false)
        addAnimationByPrefix('cpSRW', '1', 'number 1', 24, false)
        addAnimationByPrefix('cpSRW', '2', 'number 2', 24, false)
        addAnimationByPrefix('cpSRW', '3', 'number 3', 24, false)
        addAnimationByPrefix('cpSRW', '4', 'number 4', 24, false)
        addAnimationByPrefix('cpSRW', '5', 'number 5', 24, false)
        addAnimationByPrefix('cpSRW', '6', 'number 6', 24, false)
        addAnimationByPrefix('cpSRW', '7', 'number 7', 24, false)
        addAnimationByPrefix('cpSRW', '8', 'number 8', 24, false)
        addAnimationByPrefix('cpSRW', '9', 'number 9', 24, false)
        setObjectCamera('cpSRW', 'other')
        setProperty('cpSRW.alpha', 0)
        addLuaSprite('cpSRW', true)
        
        makeLuaSprite('cpTS', 'clearPercent/clearPercentTextSmall', 658 + getProperty('difficultyTextRS.width'), 125 - 6)
        setObjectCamera('cpTS', 'other')
        setProperty('cpTS.alpha', 0)
        addLuaSprite('cpTS', true)

        for i = 1, #nameSong do
            if themeColor == 'Default' then
                makeAnimatedLuaSprite('songLetter'..i, 'resultsAlphabet', 670 + (i * 36) + getProperty('difficultyTextRS.width'), 5 - (i * 2.5) - getProperty('difficultyTextRS.width')/13.5)
            else
                makeAnimatedLuaSprite('songLetterB'..i, 'colorStuff/resultsAlphabetBorder-white', 670 + (i * 36) + getProperty('difficultyTextRS.width'), 5 - (i * 2.5) - getProperty('difficultyTextRS.width')/13.5)
                makeAnimatedLuaSprite('songLetter'..i, 'colorStuff/resultsAlphabet-white', 670 + (i * 36) + getProperty('difficultyTextRS.width'), 5 - (i * 2.5) - getProperty('difficultyTextRS.width')/13.5)
                setObjectCamera('songLetterB'..i, 'other')
                setProperty('songLetterB'..i..'.alpha', 0)
                setProperty('songLetterB'..i..'.angle', -4)
                setProperty('songLetterB'..i..'.color', colorD)
                addLuaSprite('songLetterB'..i, true)

                setProperty('songLetter'..i..'.color', colorB)
                setObjectOrder('songLetter'..i, getObjectOrder('songLetterB'..i) - 1)
            end
            if i == 1 then
                addAnimationByPrefix('songLetter'..i, 'default', string.upper(string.sub(nameSong, i, i)), 24, false)
                addAnimationByPrefix('songLetterB'..i, 'default', string.upper(string.sub(nameSong, i, i)), 24, false)
            else
                addAnimationByPrefix('songLetter'..i, 'default', string.sub(nameSong, i, i), 24, false)
                addAnimationByPrefix('songLetterB'..i, 'default', string.sub(nameSong, i, i), 24, false)
            end
            setObjectCamera('songLetter'..i, 'other')
            setProperty('songLetter'..i..'.alpha', 0)
            setProperty('songLetter'..i..'.angle', -4)
            addLuaSprite('songLetter'..i, true)
        end

        addLuaSprite('difficultyTextRS', true)

        makeLuaSprite('tiltedFuckThing', 'topBarBlack', -7, -200)
        setObjectCamera('tiltedFuckThing', 'other')
        addLuaSprite('tiltedFuckThing', true)

        makeAnimatedLuaSprite('soundSystem', 'soundSystem', -15, -180)
        addAnimationByPrefix('soundSystem', 'default', 'sound system', 24, false)
        setObjectCamera('soundSystem', 'other')
        setProperty('soundSystem.alpha', 0)
        addLuaSprite('soundSystem', true)

        if themeColor == 'Default' then
            makeAnimatedLuaSprite('results', 'results', -185, -10)
        else
            makeAnimatedLuaSprite('results', 'colorStuff/results-white', -185, -10)
            makeAnimatedLuaSprite('resultsShine', 'colorStuff/resultsShine-white', -185, -10)
            setProperty('results.color', color)
            setProperty('resultsShine.color', colorB)
            addAnimationByPrefix('resultsShine', 'default', 'results', 24, false)
            setObjectCamera('resultsShine', 'other')
            setProperty('resultsShine.alpha', 0)
            addLuaSprite('resultsShine', true)
        end
        addAnimationByPrefix('results', 'default', 'results', 24, false)
        setObjectCamera('results', 'other')
        setProperty('results.alpha', 0)
        addLuaSprite('results', true)

        makeAnimatedLuaSprite('ratingsPopin', 'ratingsPopin', -135, 135)
        addAnimationByPrefix('ratingsPopin', 'default', 'Categories', 24, false)
        setObjectCamera('ratingsPopin', 'other')
        setProperty('ratingsPopin.alpha', 0)
        addLuaSprite('ratingsPopin', true)

        makeAnimatedLuaSprite('scorePopin', 'scorePopin', -180, 515)
        addAnimationByPrefix('scorePopin', 'default', 'tally', 24, false)
        setObjectCamera('scorePopin', 'other')
        setProperty('scorePopin.alpha', 0)
        addLuaSprite('scorePopin', true)

        makeAnimatedLuaSprite('highscoreNew', 'highscoreNew', 45, 555)
        addAnimationByPrefix('highscoreNew', 'default', 'highscore', 24, false)
        setObjectCamera('highscoreNew', 'other')
        setProperty('highscoreNew.alpha', 0)
        addLuaSprite('highscoreNew', true)

        for i = 10, 1, -1 do
            makeAnimatedLuaSprite('digNum'..i, 'score-digital-numbers', 5 + (i*67), 610)
            addAnimationByPrefix('digNum'..i, '0', 'ZERO', 24, false)
            addAnimationByPrefix('digNum'..i, '1', 'ONE', 24, false)
            addAnimationByPrefix('digNum'..i, '2', 'TWO', 24, false)
            addAnimationByPrefix('digNum'..i, '3', 'THREE', 24, false)
            addAnimationByPrefix('digNum'..i, '4', 'FOUR', 24, false)
            addAnimationByPrefix('digNum'..i, '5', 'FIVE', 24, false)
            addAnimationByPrefix('digNum'..i, '6', 'SIX', 24, false)
            addAnimationByPrefix('digNum'..i, '7', 'SEVEN', 24, false)
            addAnimationByPrefix('digNum'..i, '8', 'EIGHT', 24, false)
            addAnimationByPrefix('digNum'..i, '9', 'NINE', 24, false)
            addAnimationByPrefix('digNum'..i, 'disabled', 'DISABLED', 24, false)
            addAnimationByPrefix('digNum'..i, 'gone', 'GONE', 24, false)
            addAnimationByPrefix('digNum'..i, 'shuffle', 'SHUFFLE', 24, true)
            addAnimationByPrefix('digNum'..i, 'shuffleSlow', 'SHUFFLE', 12, true)
            setObjectCamera('digNum'..i, 'other')
            setProperty('digNum'..i..'.alpha', 0)
            addLuaSprite('digNum'..i, true)
        end

        makeLuaSprite('superCoolResultsScreenOverlayJustForThisMod', '', -10, -10)
        makeGraphic('superCoolResultsScreenOverlayJustForThisMod', 1300, 740, '000000')
        setObjectCamera('superCoolResultsScreenOverlayJustForThisMod', 'other')
        setProperty('superCoolResultsScreenOverlayJustForThisMod.alpha', 0)
        addLuaSprite('superCoolResultsScreenOverlayJustForThisMod', true)

        songOver = true
        doTweenAlpha('startUpThisShit', 'superCoolResultsScreenOverlayJustForThisMod', 1, 0.5, 'linear')
        return Function_Stop;
    end
end

function isHovering(tag, camera)
    camera = camera or 'hud' -- Default to 'hud' if omitted
    
    local mx = getMouseX(camera)
    local my = getMouseY(camera)
    
    local x = getProperty(tag .. '.x')
    local y = getProperty(tag .. '.y')
    local w = getProperty(tag .. '.width')
    local h = getProperty(tag .. '.height')
    
    return (mx >= x and mx <= x + w and my >= y and my <= y + h)
end

function onUpdate(elapsed)
    if songOver then
        if mouseClicked('LEFT') and isHovering('backButton', 'other') then
            doTweenAlpha('itsOverPal', 'superCoolResultsScreenOverlayJustForThisMod', 1, 0.55, 'linear')
            playAnim('backButton', 'back')
            setProperty('backButton.alpha', 1)
            doTweenAlpha('backButtonOut', 'backButton', 0, 0.5, 'linear')
            if char == 'bf' then
                if accuracyNum == 100 then
                    playMusic('resultsPERFECT-exit', 0.8)
                elseif accuracyNum > 89 and accuracyNum < 100 then
                    playMusic('resultsEXCELLENT-exit', 0.8)
                elseif accuracyNum > 79 and accuracyNum < 90 then
                    playMusic('resultsNORMAL-exit', 0.8)
                elseif accuracyNum > 59 and accuracyNum < 80 then
                    playMusic('resultsNORMAL-exit', 0.8)
                elseif accuracyNum < 60 then
                    playMusic('resultsSHIT-exit', 0.8)
                end
            elseif char == 'pico' then
                if accuracyNum == 100 then
                    playMusic('resultsPERFECT-pico-exit', 0.8)
                elseif accuracyNum > 89 and accuracyNum < 100 then
                    playMusic('resultsEXCELLENT-pico-exit', 0.8)
                elseif accuracyNum > 79 and accuracyNum < 90 then
                    playMusic('resultsNORMAL-pico-exit', 0.8)
                elseif accuracyNum > 59 and accuracyNum < 80 then
                    playMusic('resultsNORMAL-pico-exit', 0.8)
                elseif accuracyNum < 60 then
                    playMusic('resultsSHIT-pico-exit', 0.8)
                end
            end
        end
    end
    if getModSetting('excludeMisses', 'V-Slice Results Screen') then
        songNotes = sicks + goods + bads + shits
    else
        songNotes = sicks + goods + bads + shits + misses
    end
    fullSongNotes = sicks + goods + bads + shits + misses
    if debugMode then
        if keyboardJustPressed('BACKSPACE') then
            restartSong()
        end
        if keyboardJustPressed('ESCAPE') then
            endSong()
        end
    end
    if keyboardJustPressed('ENTER') then
        if songOver == true then
            if char == 'bf' then
                if accuracyNum == 100 then
                    playMusic('resultsPERFECT-exit', 0.8)
                elseif accuracyNum > 89 and accuracyNum < 100 then
                    playMusic('resultsEXCELLENT-exit', 0.8)
                elseif accuracyNum > 79 and accuracyNum < 90 then
                    playMusic('resultsNORMAL-exit', 0.8)
                elseif accuracyNum > 59 and accuracyNum < 80 then
                    playMusic('resultsNORMAL-exit', 0.8)
                elseif accuracyNum < 60 then
                    playMusic('resultsSHIT-exit', 0.8)
                end
            elseif char == 'pico' then
                if accuracyNum == 100 then
                    playMusic('resultsPERFECT-pico-exit', 0.8)
                elseif accuracyNum > 89 and accuracyNum < 100 then
                    playMusic('resultsEXCELLENT-pico-exit', 0.8)
                elseif accuracyNum > 79 and accuracyNum < 90 then
                    playMusic('resultsNORMAL-pico-exit', 0.8)
                elseif accuracyNum > 59 and accuracyNum < 80 then
                    playMusic('resultsNORMAL-pico-exit', 0.8)
                elseif accuracyNum < 60 then
                    playMusic('resultsSHIT-pico-exit', 0.8)
                end
            end
            doTweenAlpha('itsOverPal', 'superCoolResultsScreenOverlayJustForThisMod', 1, 0.55, 'linear')
        end
    end
end

function onUpdatePost(elapsed)
    if accuracyStyle == 'vslice' then
        vFakeAcc = math.floor(vsliceAccuracyCalc(fullSongNotes, sicks or 0, goods or 0) * 100)
        vAcc = vFakeAcc / 100
        if vAcc == 100 then
            vRating = 'PERFECT'
        elseif vAcc > 89.99 and vAcc < 100 then
            vRating = 'EXCELLENT'
        elseif vAcc > 79.99 and vAcc < 90 then
            vRating = 'GREAT'
        elseif vAcc > 59.99 and vAcc < 80 then
            vRating = 'GOOD'
        elseif vAcc < 60 then
            vRating = 'LOSS'
        end
        setTextString('scoreTxt', 'Score: '..getProperty('songScore')..' | Misses: '..getProperty('songMisses')..' | Rating: '..vRating..' ('..vAcc..'%) - '..getProperty('ratingFC'))
    end
end

function onTimerCompleted(tag, loops, loopsLeft)
    if tag == 'endThisHoeNOWWWWW' then
        doTweenAlpha('itsOverPal', 'superCoolResultsScreenOverlayJustForThisMod', 1, 0.55, 'linear')
    end
    if tag == 'yoWait' then
        if getModSetting('mobileHelp', 'V-Slice Results Screen') == 'Exit Button' then
            makeAnimatedLuaSprite('backButton', 'backButton', 1090, -10)
            addAnimationByIndices('backButton', 'back', 'back', '4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22', 24)
            addAnimationByIndices('backButton', 'idle', 'back', '1', 1)
            setObjectCamera('backButton', 'other')
            scaleObject('backButton', 0.67, 0.67)
            setProperty('backButton.alpha', 0)
            addLuaSprite('backButton', true)
            playAnim('backButton', 'idle', true)
            doTweenAlpha('backButtonIn', 'backButton', 0.5, 0.5, 'linear')
        elseif getModSetting('mobileHelp', 'V-Slice Results Screen') == 'Auto Exit' then
            runTimer('endThisHoeNOWWWWW', 10)
        end
        if char == 'bf' then
            if accuracyNum > 89 and accuracyNum < 100 then
                playMusic('resultsEXCELLENT-intro', 0.8)
                runTimer('playBFExcellentLoop', 5.1)
            elseif accuracyNum > 79 and accuracyNum < 90 then
                playMusic('resultsNORMAL', 0.8, true)
            elseif accuracyNum > 59 and accuracyNum < 80 then
                playMusic('resultsNORMAL', 0.8, true)
            elseif accuracyNum < 60 then
                playMusic('resultsSHIT-intro', 0.8)
                runTimer('playBFShitLoop', 16)
            end
        elseif char == 'pico' then
            if accuracyNum > 89 and accuracyNum < 100 then
                playMusic('resultsEXCELLENT-pico-intro', 0.8)
                runTimer('playPicoExcellentLoop', 104.7)
            elseif accuracyNum > 79 and accuracyNum < 90 then
                playMusic('resultsNORMAL-pico', 0.8, true)
            elseif accuracyNum > 59 and accuracyNum < 80 then
                playMusic('resultsNORMAL-pico', 0.8, true)
            elseif accuracyNum < 60 then
                playMusic('resultsSHIT-pico', 0.8)
            end
        end
        doTweenY('scrollTheFuck', 'tiltedFuckThing', 0, 0.5, 'quadInOut')
        setProperty('superCoolResultsScreenBackground.alpha', 1)
        setProperty('soundSystem.alpha', 1)
        playAnim('soundSystem', 'default', true)
        setProperty('results.alpha', 1)
        if themeColor ~= 'Default' then
            setProperty('resultsShine.alpha', 1)
            playAnim('resultsShine', 'default', true)
        end
        playAnim('results', 'default', true)
        runTimer('popinAndDiffStuff', 0.55)
        doTweenAlpha('fadeOutMotherfucka', 'superCoolResultsScreenOverlayJustForThisMod', 0, 0.25, 'linear')
    end
    if tag == 'perfectPicoAnimLoop' then
        setProperty('resultsAnim1.visible', true)
        setProperty('resultsAnim.visible', false)
        playAnim('resultsAnim1', 'resultsLoop', true)
    end
    if tag == 'popinAndDiffStuff' then
        setProperty('ratingsPopin.alpha', 1)
        playAnim('ratingsPopin', 'default', true)
        setProperty('difficultyTextRS.alpha', 1)
        doTweenY('differDowners', 'difficultyTextRS', 125, 0.3, 'quadOut')

        for i = 1, #nameSong do
            setProperty('songLetter'..i..'.alpha', 1)
            if themeColor ~= 'Default' then
                setProperty('songLetterB'..i..'.alpha', 1)
                if nightmare then
                    doTweenY('moveLetterB'..i, 'songLetterB'..i, getProperty('songLetterB'..i..'.y') + 130, 0.3, 'quadOut')
                else
                    doTweenY('moveLetterB'..i, 'songLetterB'..i, getProperty('songLetterB'..i..'.y') + 122, 0.3, 'quadOut')
                end
            end
            if nightmare then
                doTweenY('moveLetter'..i, 'songLetter'..i, getProperty('songLetter'..i..'.y') + 130, 0.3, 'quadOut')
            else
                doTweenY('moveLetter'..i, 'songLetter'..i, getProperty('songLetter'..i..'.y') + 122, 0.3, 'quadOut')
            end
        end

        runTimer('numbersStart', 0.3)
        runTimer('scoreAndAccuracy', 0.55)
    end
    if tag == 'scoreAndAccuracy' then
        setProperty('scorePopin.alpha', 1)
        playAnim('scorePopin', 'default', true)
        if score > highScore then
            setProperty('highscoreNew.alpha', 1)
            playAnim('highscoreNew', 'default', true)
        end
        setProperty('cpText.alpha', 1)

        scoreStr = tostring(score)
        digLen = #scoreStr

        for i = 10, 1, -1 do
            setProperty('digNum'..i..'.alpha', 1)

            strIndex = digLen - (10 - i)

            if strIndex < 1 then
                playAnim('digNum'..i, 'disabled', true)
            else
                playAnim('digNum'..i, 'gone', true)
                runTimer('disableNum'..i, 0.1 + (i * 0.05))
                runTimer('zeroNum'..i, 0.125 + (i * 0.05))
                runTimer('shuffleNum'..i, 0.15 + (i * 0.05))
                runTimer('slowShuffleNum'..i, 1.25 + (i * 0.05))
                runTimer('displayNum'..i, 2 + (i * 0.05))
            end
        end

        riseAccuracy = 0
        playAnim('cpR', '0')
        playAnim('cpRW', '0')
        setProperty('cpR.alpha', 1)

        for i = 1, accuracyNum do
            runTimer('riseAcc'..i, 0.03 + math.pow(i / accuracyNum, 12) * 2.47)
        end
        playAnim('cp1', '1', true)
        playAnim('cp1W', '1', true)

        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0.6)
        doTweenAlpha('tWUWIAHDS', 'superCoolResultsScreenBackgroundFlash', 0, 0.3, 'linear')
    end
    for i = 1, accuracyNum do
        if tag == 'riseAcc'..i then
            riseAccuracy = riseAccuracy + 1
            if riseAccuracy < 10 then
                playAnim('cpR', tostring(riseAccuracy))
                playAnim('cpRW', tostring(riseAccuracy))
                setProperty('cpR.alpha', 1)
                playSound('scrollMenu', 0.8)
            elseif riseAccuracy < 100 and riseAccuracy > 9 then
                setProperty('cpL.alpha', 1)
                playAnim('cpL', string.sub(tostring(riseAccuracy), 1, 1))
                playAnim('cpR', string.sub(tostring(riseAccuracy), 2, 2))
                playAnim('cpLW', string.sub(tostring(riseAccuracy), 1, 1))
                playAnim('cpRW', string.sub(tostring(riseAccuracy), 2, 2))
                playSound('scrollMenu', 0.8)
            elseif riseAccuracy == 100 then
                setProperty('cp1.alpha', 1)
                playAnim('cpL', '0')
                playAnim('cpR', '0')
                playAnim('cpLW', '0')
                playAnim('cpRW', '0')
            end
            if riseAccuracy == accuracyNum then
                if accuracyNum == 100 then
                    if char == 'bf' then
                        playMusic('resultsPERFECT', 0.8, true)
                    elseif char == 'pico' then
                        playMusic('resultsPERFECT-pico-intro', 0.8)
                        runTimer('playPicoPerfectLoop', 64.6)
                    end
                end
                playSound('confirmMenu', 0.8)
                setProperty('cpTS.alpha', 1)
                if riseAccuracy == 100 then
                    setProperty('cp1W.alpha', 1)
                    setProperty('cp1.alpha', 0)
                    setProperty('cp1SW.alpha', 1)
                    setProperty('cp1S.alpha', 0)
                    setProperty('cpLW.alpha', 1)
                    setProperty('cpSLW.alpha', 1)
                    playAnim('cpSL', '0')
                    playAnim('cpSR', '0')
                    playAnim('cpSLW', '0')
                    playAnim('cpSRW', '0')
                elseif riseAccuracy > 9 and riseAccuracy < 100 then
                    setProperty('cpLW.alpha', 1)
                    setProperty('cpSLW.alpha', 1)
                    setProperty('cpL.alpha', 0)
                    setProperty('cpSL.alpha', 0)
                    playAnim('cpSL', string.sub(tostring(riseAccuracy), 1, 1))
                    playAnim('cpSR', string.sub(tostring(riseAccuracy), 2, 2))
                    playAnim('cpSLW', string.sub(tostring(riseAccuracy), 1, 1))
                    playAnim('cpSRW', string.sub(tostring(riseAccuracy), 2, 2))
                elseif riseAccuracy < 10 then
                    playAnim('cpSR', string.sub(tostring(riseAccuracy), 1, 1))
                    playAnim('cpSRW', string.sub(tostring(riseAccuracy), 1, 1))
                end
                startAnims()
                setProperty('cpSRW.alpha', 1)
                setProperty('cpRW.alpha', 1)
                setProperty('cpSR.alpha', 0)
                setProperty('cpR.alpha', 0)
                runTimer('getTheFuckOut', 0.25)
                runTimer('songNameMove', 3)
            end
        end
    end
    if tag == 'getTheFuckOut' then
        if riseAccuracy == 100 then
            setProperty('cp1W.alpha', 0)
            setProperty('cp1.alpha', 1)
            setProperty('cp1SW.alpha', 0)
            setProperty('cp1S.alpha', 1)
        end
        if riseAccuracy > 10 then
            setProperty('cpLW.alpha', 0)
            setProperty('cpSLW.alpha', 0)
            setProperty('cpL.alpha', 1)
            setProperty('cpSL.alpha', 1)
        end
        setProperty('cpSRW.alpha', 0)
        setProperty('cpRW.alpha', 0)
        setProperty('cpSR.alpha', 1)
        setProperty('cpR.alpha', 1)
        doTweenAlpha('cpTextOut', 'cpText', 0, 0.75, 'quadIn')
        doTweenAlpha('cp1Out', 'cp1', 0, 0.75, 'quadIn')
        doTweenAlpha('cpLOut', 'cpL', 0, 0.75, 'quadIn')
        doTweenAlpha('cpROut', 'cpR', 0, 0.75, 'quadIn')
    end
    for i = 1, 10 do
        if tag == 'disableNum'..i then
            playAnim('digNum'..i, 'disabled', true)
        end
        if tag == 'zeroNum'..i then
            playAnim('digNum'..i, 'zero', true)
        end
        if tag == 'shuffleNum'..i then
            playAnim('digNum'..i, 'shuffle', true)
            setProperty('digNum'..i..'.animation.curAnim.curFrame', math.random(0, 9))
        end
        if tag == 'slowShuffleNum'..i then
            playAnim('digNum'..i, 'shuffleSlow', true)
            setProperty('digNum'..i..'.animation.curAnim.curFrame', math.random(0, 9))
        end
        if tag == 'displayNum'..i then
            playAnim('digNum'..i, string.sub(scoreStr, digLen - (10 - i), digLen - (10 - i)), true)
        end
    end
    if tag == 'numbersStart' then
        songNotesNum = 0
        maxComboNum = 0
        sicksNum = 0
        goodsNum = 0
        badsNum = 0
        shitsNum = 0
        missesNum = 0

        delay = 0
        maxComboStr = tostring(maxCombo)

        for i = 1, #notesStr do
            makeAnimatedLuaSprite('totalTallieNum'..i, 'tallieNumber', 330 + (i*40), 147)
            setObjectCamera('totalTallieNum'..i, 'other')
            setObjectOrder('totalTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('totalTallieNum'..i..'.alpha', 0)
            addAnimationByPrefix('totalTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('totalTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('totalTallieNum'..i)
        end
        for i = 1, #maxComboStr do
            makeAnimatedLuaSprite('maxTallieNum'..i, 'tallieNumber', 330 + (i*40), 202)
            setObjectCamera('maxTallieNum'..i, 'other')
            setObjectOrder('maxTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('maxTallieNum'..i..'.alpha', 0)
            addAnimationByPrefix('maxTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('maxTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('maxTallieNum'..i)
        end
        for i = 1, #sicksStr do
            makeAnimatedLuaSprite('sickTallieNum'..i, 'tallieNumber', 185 + (i*40), 267)
            setObjectCamera('sickTallieNum'..i, 'other')
            setObjectOrder('sickTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('sickTallieNum'..i..'.alpha', 0)
            setProperty('sickTallieNum'..i..'.color', 0x89e0a0)
            addAnimationByPrefix('sickTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('sickTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('sickTallieNum'..i)
        end
        for i = 1, #goodsStr do
            makeAnimatedLuaSprite('goodTallieNum'..i, 'tallieNumber', 165 + (i*40), 322)
            setObjectCamera('goodTallieNum'..i, 'other')
            setObjectOrder('goodTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('goodTallieNum'..i..'.alpha', 0)
            setProperty('goodTallieNum'..i..'.color', 0x8cc7e0)
            addAnimationByPrefix('goodTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('goodTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('goodTallieNum'..i)
        end
        for i = 1, #badsStr do
            makeAnimatedLuaSprite('badTallieNum'..i, 'tallieNumber', 145 + (i*40), 382)
            setObjectCamera('badTallieNum'..i, 'other')
            setObjectOrder('badTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('badTallieNum'..i..'.alpha', 0)
            setProperty('badTallieNum'..i..'.color', 0xe6d18e)
            addAnimationByPrefix('badTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('badTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('badTallieNum'..i)
        end
        for i = 1, #shitsStr do
            makeAnimatedLuaSprite('shitTallieNum'..i, 'tallieNumber', 175 + (i*40), 440)
            setObjectCamera('shitTallieNum'..i, 'other')
            setObjectOrder('shitTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('shitTallieNum'..i..'.alpha', 0)
            setProperty('shitTallieNum'..i..'.color', 0xe58d8b)
            addAnimationByPrefix('shitTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('shitTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('shitTallieNum'..i)
        end
        for i = 1, #missesStr do
            makeAnimatedLuaSprite('missTallieNum'..i, 'tallieNumber', 205 + (i*40), 497)
            setObjectCamera('missTallieNum'..i, 'other')
            setObjectOrder('missTallieNum'..i, getObjectOrder('superCoolResultsScreenOverlayJustForThisMod') - 1)
            setProperty('missTallieNum'..i..'.alpha', 0)
            setProperty('missTallieNum'..i..'.color', 0xc38be0)
            addAnimationByPrefix('missTallieNum'..i, '0', '0', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '1', '1', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '2', '2', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '3', '3', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '4', '4', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '5', '5', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '6', '6', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '7', '7', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '8', '8', 1, false)
            addAnimationByPrefix('missTallieNum'..i, '9', '9', 1, false)
            addLuaSprite('missTallieNum'..i)
        end

        duration = 2.42
        addDelay = 0.2

        for i = 1, songNotes do
            delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
            runTimer('songNotesUp'..i, delay)
        end
        delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
        for i = 1, maxCombo do
            delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
            runTimer('maxComboUp'..i, delay)
        end
        delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
        if sicks > 0 then
            for i = 1, sicks do
                delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
                runTimer('sicksUp'..i, delay)
            end
        else
            delay = delay + 0.1
            runTimer('sicks0', delay)
        end
        delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
        if goods > 0 then
            for i = 1, goods do
                delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
                runTimer('goodsUp'..i, delay)
            end
        else
            delay = delay + 0.1
            runTimer('goods0', delay)
        end
        delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
        if bads > 0 then
            for i = 1, bads do
                delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
                runTimer('badsUp'..i, delay)
            end
        else
            delay = delay + 0.1
            runTimer('bads0', delay)
        end
        delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
        if shits > 0 then
            for i = 1, shits do
                delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
                runTimer('shitsUp'..i, delay)
            end
        else
            delay = delay + 0.1
            runTimer('shits0', delay)
        end
        delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
        if misses > 0 then
            for i = 1, misses do
                delay = delay + (duration / (songNotes + maxCombo + sicks + goods + bads + shits + misses + 6))
                runTimer('missesUp'..i, delay)
            end
        else
            delay = delay + 0.1
            runTimer('misses0', delay)
        end
    end
    for i = 1, songNotes do
        if tag == 'songNotesUp'..i then
            songNotesNum = songNotesNum + 1
            playAnim('totalTallieNum1', string.sub(songNotesNum, 1, 1), true)
            setProperty('totalTallieNum1.alpha', 1)
            if songNotesNum > 9 then
                playAnim('totalTallieNum2', string.sub(songNotesNum, 2, 2), true)
                setProperty('totalTallieNum2.alpha', 1)
            end
            if songNotesNum > 99 then
                playAnim('totalTallieNum3', string.sub(songNotesNum, 3, 3), true)
                setProperty('totalTallieNum3.alpha', 1)
            end
            if songNotesNum > 999 then
                playAnim('totalTallieNum4', string.sub(songNotesNum, 4, 4), true)
                setProperty('totalTallieNum4.alpha', 1)
            end
        end
    end
    for i = 1, maxCombo do
        if tag == 'maxComboUp'..i then
            maxComboNum = maxComboNum + 1
            playAnim('maxTallieNum1', string.sub(maxComboNum, 1, 1), true)
            setProperty('maxTallieNum1.alpha', 1)
            if maxComboNum > 9 then
                playAnim('maxTallieNum2', string.sub(maxComboNum, 2, 2), true)
                setProperty('maxTallieNum2.alpha', 1)
            end
            if maxComboNum > 99 then
                playAnim('maxTallieNum3', string.sub(maxComboNum, 3, 3), true)
                setProperty('maxTallieNum3.alpha', 1)
            end
            if maxComboNum > 999 then
                playAnim('maxTallieNum4', string.sub(maxComboNum, 4, 4), true)
                setProperty('maxTallieNum4.alpha', 1)
            end
        end
    end
    for i = 1, sicks do
        if tag == 'sicksUp'..i then
            sicksNum = sicksNum + 1
            playAnim('sickTallieNum1', string.sub(sicksNum, 1, 1), true)
            setProperty('sickTallieNum1.alpha', 1)
            if sicksNum > 9 then
                playAnim('sickTallieNum2', string.sub(sicksNum, 2, 2), true)
                setProperty('sickTallieNum2.alpha', 1)
            end
            if sicksNum > 99 then
                playAnim('sickTallieNum3', string.sub(sicksNum, 3, 3), true)
                setProperty('sickTallieNum3.alpha', 1)
            end
            if sicksNum > 999 then
                playAnim('sickTallieNum4', string.sub(sicksNum, 4, 4), true)
                setProperty('sickTallieNum4.alpha', 1)
            end
        end
    end
    if tag == 'sicks0' then
        playAnim('sickTallieNum1', string.sub(sicksNum, 1, 1), true)
        setProperty('sickTallieNum1.alpha', 1)
    end
    for i = 1, goods do
        if tag == 'goodsUp'..i then
            goodsNum = goodsNum + 1
            playAnim('goodTallieNum1', string.sub(goodsNum, 1, 1), true)
            setProperty('goodTallieNum1.alpha', 1)
            if goodsNum > 9 then
                playAnim('goodTallieNum2', string.sub(goodsNum, 2, 2), true)
                setProperty('goodTallieNum2.alpha', 1)
            end
            if goodsNum > 99 then
                playAnim('goodTallieNum3', string.sub(goodsNum, 3, 3), true)
                setProperty('goodTallieNum3.alpha', 1)
            end
            if goodsNum > 999 then
                playAnim('goodTallieNum4', string.sub(goodsNum, 4, 4), true)
                setProperty('goodTallieNum4.alpha', 1)
            end
        end
    end
    if tag == 'goods0' then
        playAnim('goodTallieNum1', string.sub(goodsNum, 1, 1), true)
        setProperty('goodTallieNum1.alpha', 1)
    end
    for i = 1, bads do
        if tag == 'badsUp'..i then
            badsNum = badsNum + 1
            playAnim('badTallieNum1', string.sub(badsNum, 1, 1), true)
            setProperty('badTallieNum1.alpha', 1)
            if badsNum > 9 then
                playAnim('badTallieNum2', string.sub(badsNum, 2, 2), true)
                setProperty('badTallieNum2.alpha', 1)
            end
            if badsNum > 99 then
                playAnim('badTallieNum3', string.sub(badsNum, 3, 3), true)
                setProperty('badTallieNum3.alpha', 1)
            end
            if badsNum > 999 then
                playAnim('badTallieNum4', string.sub(badsNum, 4, 4), true)
                setProperty('badTallieNum4.alpha', 1)
            end
        end
    end
    if tag == 'bads0' then
        playAnim('badTallieNum1', string.sub(badsNum, 1, 1), true)
        setProperty('badTallieNum1.alpha', 1)
    end
    for i = 1, shits do
        if tag == 'shitsUp'..i then
            shitsNum = shitsNum + 1
            playAnim('shitTallieNum1', string.sub(shitsNum, 1, 1), true)
            setProperty('shitTallieNum1.alpha', 1)
            if shitsNum > 9 then
                playAnim('shitTallieNum2', string.sub(shitsNum, 2, 2), true)
                setProperty('shitTallieNum2.alpha', 1)
            end
            if shitsNum > 99 then
                playAnim('shitTallieNum3', string.sub(shitsNum, 3, 3), true)
                setProperty('shitTallieNum3.alpha', 1)
            end
            if shitsNum > 999 then
                playAnim('shitTallieNum4', string.sub(shitsNum, 4, 4), true)
                setProperty('shitTallieNum4.alpha', 1)
            end
        end
    end
    if tag == 'shits0' then
        playAnim('shitTallieNum1', string.sub(shitsNum, 1, 1), true)
        setProperty('shitTallieNum1.alpha', 1)
    end
    for i = 1, misses do
        if tag == 'missesUp'..i then
            missesNum = missesNum + 1
            playAnim('missTallieNum1', string.sub(missesNum, 1, 1), true)
            setProperty('missTallieNum1.alpha', 1)
            if missesNum > 9 then
                playAnim('missTallieNum2', string.sub(missesNum, 2, 2), true)
                setProperty('missTallieNum2.alpha', 1)
            end
            if missesNum > 99 then
                playAnim('missTallieNum3', string.sub(missesNum, 3, 3), true)
                setProperty('missTallieNum3.alpha', 1)
            end
            if missesNum > 999 then
                playAnim('missTallieNum4', string.sub(missesNum, 4, 4), true)
                setProperty('missTallieNum4.alpha', 1)
            end
        end 
    end
    if tag == 'misses0' then
        playAnim('missTallieNum1', string.sub(missesNum, 1, 1), true)
        setProperty('missTallieNum1.alpha', 1)
    end
    if tag == 'songNameMove' then
        textMoveX = 1800
        textMoveY = -130
        moveTime = 10
        doTweenX('difficultyTextRSX', 'difficultyTextRS', getProperty('difficultyTextRS.x') - textMoveX, moveTime, 'linear')
        doTweenX('cp1SX', 'cp1S', getProperty('cp1S.x') - textMoveX, moveTime, 'linear')
        doTweenX('cpSLX', 'cpSL', getProperty('cpSL.x') - textMoveX, moveTime, 'linear')
        doTweenX('cpSRX', 'cpSR', getProperty('cpSR.x') - textMoveX, moveTime, 'linear')
        doTweenX('cpTSX', 'cpTS', getProperty('cpTS.x') - textMoveX, moveTime, 'linear')
        doTweenY('difficultyTextRSY', 'difficultyTextRS', getProperty('difficultyTextRS.y') - textMoveY, moveTime, 'linear')
        doTweenY('cp1SY', 'cp1S', getProperty('cp1S.y') - textMoveY, moveTime, 'linear')
        doTweenY('cpSLY', 'cpSL', getProperty('cpSL.y') - textMoveY, moveTime, 'linear')
        doTweenY('cpSRY', 'cpSR', getProperty('cpSR.y') - textMoveY, moveTime, 'linear')
        doTweenY('cpTSY', 'cpTS', getProperty('cpTS.y') - textMoveY, moveTime, 'linear')
        for i = 1, #nameSong do
            doTweenX('songLetterX'..i, 'songLetter'..i, getProperty('songLetter'..i..'.x') - textMoveX, moveTime, 'linear')
            doTweenY('songLetterY'..i, 'songLetter'..i, getProperty('songLetter'..i..'.y') - textMoveY, moveTime, 'linear')
            if themeColor ~= 'Default' then
                doTweenX('songLetterXB'..i, 'songLetterB'..i, getProperty('songLetterB'..i..'.x') - textMoveX, moveTime, 'linear')
                doTweenY('songLetterYB'..i, 'songLetterB'..i, getProperty('songLetterB'..i..'.y') - textMoveY, moveTime, 'linear')
            end
        end
    end
    if tag == 'lossShow' then
        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0.6)
        doTweenAlpha('tWUWIAHDS', 'superCoolResultsScreenBackgroundFlash', 0, 0.3, 'linear')
        for i = 1, 4 do
            makeLuaSprite('lossText'..i, 'rankText/rankTextLOSS', 1235, -180 + (i * 275))
            setObjectCamera('lossText'..i, 'other')
            setObjectOrder('lossText'..i, getObjectOrder('resultsAnim') + 1)
            addLuaSprite('lossText'..i)
        end
        lossScrollX = 500
        lossScrollY = 26
        lossScrollTime = 50
        for i = 1, 4 do
            for j = 1, 9 do
                if themeColor == 'Default' then
                    makeLuaSprite('lossScroll'..j..i, 'rankText/rankScrollLOSS', - 600 + (i * 500), 90 + (j * 67) - (i-1)*28)
                else
                    makeLuaSprite('lossScroll'..j..i, 'rankText/colorStuff/rankScrollLOSS-white', - 600 + (i * 500), 90 + (j * 67) - (i-1)*28)
                    setProperty('lossScroll'..j..i..'.color', colorB)
                end
                setProperty('lossScroll'..j..i..'.angle', -3)
                setObjectCamera('lossScroll'..j..i, 'other')
                setObjectOrder('lossScroll'..j..i, getObjectOrder('superCoolResultsScreenBackground') + 1)
                addLuaSprite('lossScroll'..j..i)
                if j % 2 == 1 then
                    doTweenX('lossScrollMoveX'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.x') - lossScrollX, lossScrollTime, 'linear')
                    doTweenY('lossScrollMoveY'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.y') + lossScrollY, lossScrollTime, 'linear')
                else
                    doTweenX('lossScrollMoveX'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.x') + lossScrollX, lossScrollTime, 'linear')
                    doTweenY('lossScrollMoveY'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.y') - lossScrollY, lossScrollTime, 'linear')
                end
            end
        end
        runTimer('lossTextFlicker1', 0.1)
        runTimer('lossTextFlicker2', 0.2)
        runTimer('lossTextScroll', 2)
    end
    if tag == 'lossTextFlicker1' then
        for i = 1, 4 do
            setProperty('lossText'..i..'.alpha', 0)
        end
    end
    if tag == 'lossTextFlicker2' then
        for i = 1, 4 do
            setProperty('lossText'..i..'.alpha', 1)
        end
    end
    if tag == 'lossTextScroll' then
        for i = 1, 4 do
            doTweenY('lossTextUp'..i, 'lossText'..i, getProperty('lossText'..i..'.y') - 275, 4, 'linear')
        end
    end
    if tag == 'playBFShitLoop' then
        playMusic('resultsSHIT', 0.8, true)
    end
    if tag == 'playBFExcellentLoop' then
        playMusic('resultsEXCELLENT', 0.8, true)
    end
    if tag == 'playPicoExcellentLoop' then
        playMusic('resultsEXCELLENT-pico', 0.8, true)
    end
    if tag == 'playPicoPerfectLoop' then
        playMusic('resultsPERFECT-pico', 0.8, true)
    end
    if tag == 'resultsAnimLoop' then
        playAnim('resultsAnim', 'resultsLoop', true)
    end
    if tag == 'resultsGFLoop' then
        playAnim('resultsGF', 'resultsLoop', true)
        if themeColor ~= 'Default' then
            playAnim('resultsGFW', 'resultsLoop', true)
        end
    end
    if tag == 'resultsGF' then
        playAnim('resultsGF', 'resultsIntro', true)
        setProperty('resultsGF.visible', true)
        runTimer('resultsGFLoop', 0.2916666667)
        if themeColor ~= 'Default' then
            playAnim('resultsGFW', 'resultsIntro', true)
            setProperty('resultsGFW.visible', true)
        end
    end
    if tag == 'heartIntro' then
        playAnim('hearts', 'heartsIntro', true)
        setProperty('hearts.visible', true)
        runTimer('heartLoop', 1.75)
    end
    if tag == 'heartLoop' then
        playAnim('hearts', 'heartsLoop', true)
    end
    if tag == 'tickleFightIntro' then
        playSound('tickleFight')
        playAnim('tickleFight', 'tickleFightIntro', true)
        setProperty('tickleFight.visible', true)
        runTimer('tickleFightLoop', 0.66667)
    end
    if tag == 'tickleFightLoop' then
        playAnim('tickleFight', 'tickleFightLoop', true)
    end
    if tag == 'perfectShow' then
        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0.6)
        doTweenAlpha('tWUWIAHDS', 'superCoolResultsScreenBackgroundFlash', 0, 0.3, 'linear')
        for i = 1, 4 do
            makeLuaSprite('perfectText'..i, 'rankText/rankTextPERFECT', 1235, -360 + (i * 464))
            setObjectCamera('perfectText'..i, 'other')
            setObjectOrder('perfectText'..i, getObjectOrder('resultsAnim') + 1)
            addLuaSprite('perfectText'..i)
        end
        perfectScrollX = 825
        perfectScrollY = 43
        perfectScrollTime = 70
        for i = 1, 4 do
            for j = 1, 9 do
                if themeColor == 'Default' then
                    makeLuaSprite('perfectScroll'..j..i, 'rankText/rankScrollPERFECT', - 1200 + (i * 825), 90 + (j * 67) - (i-1)*43)
                else
                    makeLuaSprite('perfectScroll'..j..i, 'rankText/colorStuff/rankScrollPERFECT-white', - 1200 + (i * 825), 90 + (j * 67) - (i-1)*43)
                    setProperty('perfectScroll'..j..i..'.color', colorB)
                end
                setProperty('perfectScroll'..j..i..'.angle', -3)
                setObjectCamera('perfectScroll'..j..i, 'other')
                setObjectOrder('perfectScroll'..j..i, getObjectOrder('superCoolResultsScreenBackground') + 1)
                addLuaSprite('perfectScroll'..j..i)
                if j % 2 == 1 then
                    doTweenX('perfectScrollMoveX'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.x') - perfectScrollX, perfectScrollTime, 'linear')
                    doTweenY('perfectScrollMoveY'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.y') + perfectScrollY, perfectScrollTime, 'linear')
                else
                    doTweenX('perfectScrollMoveX'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.x') + perfectScrollX, perfectScrollTime, 'linear')
                    doTweenY('perfectScrollMoveY'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.y') - perfectScrollY, perfectScrollTime, 'linear')
                end
            end
        end
        runTimer('perfectTextFlicker1', 0.1)
        runTimer('perfectTextFlicker2', 0.2)
        runTimer('perfectTextScroll', 2)
    end
    if tag == 'perfectTextFlicker1' then
        for i = 1, 4 do
            setProperty('perfectText'..i..'.alpha', 0)
        end
    end
    if tag == 'perfectTextFlicker2' then
        for i = 1, 4 do
            setProperty('perfectText'..i..'.alpha', 1)
        end
    end
    if tag == 'perfectTextScroll' then
        for i = 1, 4 do
            doTweenY('perfectTextUp'..i, 'perfectText'..i, getProperty('perfectText'..i..'.y') - 464, 8, 'linear')
        end
    end
    if tag == 'excellentTextFlicker1' then
        for i = 1, 4 do
            setProperty('excellentText'..i..'.alpha', 0)
        end
    end
    if tag == 'excellentTextFlicker2' then
        for i = 1, 4 do
            setProperty('excellentText'..i..'.alpha', 1)
        end
    end
    if tag == 'excellentTextScroll' then
        for i = 1, 4 do
            doTweenY('excellentTextUp'..i, 'excellentText'..i, getProperty('excellentText'..i..'.y') - 590, 9, 'linear')
        end
    end
    if tag == 'excellentShow' then
        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0.6)
        doTweenAlpha('tWUWIAHDS', 'superCoolResultsScreenBackgroundFlash', 0, 0.3, 'linear')
        for i = 1, 4 do
            makeLuaSprite('excellentText'..i, 'rankText/rankTextexcellent', 1235, -495 + (i * 590))
            setObjectCamera('excellentText'..i, 'other')
            setObjectOrder('excellentText'..i, getObjectOrder('resultsAnim') + 1)
            addLuaSprite('excellentText'..i)
        end
        excellentScrollX = 1052
        excellentScrollY = 54
        excellentScrollTime = 80
        for i = 1, 4 do
            for j = 1, 9 do
                if themeColor == 'Default' then
                    makeLuaSprite('excellentScroll'..j..i, 'rankText/rankScrollEXCELLENT', - 1600 + (i * excellentScrollX), 90 + (j * 67) - (i-1)*excellentScrollY)
                else
                    makeLuaSprite('excellentScroll'..j..i, 'rankText/colorStuff/rankScrollEXCELLENT-white', - 1600 + (i * excellentScrollX), 90 + (j * 67) - (i-1)*excellentScrollY)
                    setProperty('excellentScroll'..j..i..'.color', colorB)
                end
                setProperty('excellentScroll'..j..i..'.angle', -3)
                setObjectCamera('excellentScroll'..j..i, 'other')
                setObjectOrder('excellentScroll'..j..i, getObjectOrder('superCoolResultsScreenBackground') + 1)
                addLuaSprite('excellentScroll'..j..i)
                if j % 2 == 1 then
                    doTweenX('excellentScrollMoveX'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.x') - excellentScrollX, excellentScrollTime, 'linear')
                    doTweenY('excellentScrollMoveY'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.y') + excellentScrollY, excellentScrollTime, 'linear')
                else
                    doTweenX('excellentScrollMoveX'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.x') + excellentScrollX, excellentScrollTime, 'linear')
                    doTweenY('excellentScrollMoveY'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.y') - excellentScrollY, excellentScrollTime, 'linear')
                end
            end
        end
        runTimer('excellentTextFlicker1', 0.1)
        runTimer('excellentTextFlicker2', 0.2)
        runTimer('excellentTextScroll', 2)
    end
    if tag == 'greatTextFlicker1' then
        for i = 1, 4 do
            setProperty('greatText'..i..'.alpha', 0)
        end
    end
    if tag == 'greatTextFlicker2' then
        for i = 1, 4 do
            setProperty('greatText'..i..'.alpha', 1)
        end
    end
    if tag == 'greatTextScroll' then
        for i = 1, 4 do
            doTweenY('greatTextUp'..i, 'greatText'..i, getProperty('greatText'..i..'.y') - 338, 4.5, 'linear')
        end
    end
    if tag == 'greatShow' then
        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0.6)
        doTweenAlpha('tWUWIAHDS', 'superCoolResultsScreenBackgroundFlash', 0, 0.3, 'linear')
        for i = 1, 4 do
            makeLuaSprite('greatText'..i, 'rankText/rankTextgreat', 1235, -245 + (i * 338))
            setObjectCamera('greatText'..i, 'other')
            setObjectOrder('greatText'..i, getObjectOrder('resultsAnim') + 1)
            addLuaSprite('greatText'..i)
        end
        greatScrollX = 604
        greatScrollY = 32
        greatScrollTime = 60
        for i = 1, 4 do
            for j = 1, 9 do
                if themeColor == 'Default' then
                    makeLuaSprite('greatScroll'..j..i, 'rankText/rankScrollGREAT', - 1200 + (i * greatScrollX), 108 + (j * 67) - (i-1)*greatScrollY)
                else
                    makeLuaSprite('greatScroll'..j..i, 'rankText/colorStuff/rankScrollGREAT-white', - 1200 + (i * greatScrollX), 108 + (j * 67) - (i-1)*greatScrollY)
                    setProperty('greatScroll'..j..i..'.color', colorB)
                end
                setProperty('greatScroll'..j..i..'.angle', -3)
                setObjectCamera('greatScroll'..j..i, 'other')
                setObjectOrder('greatScroll'..j..i, getObjectOrder('superCoolResultsScreenBackground') + 1)
                addLuaSprite('greatScroll'..j..i)
                if j % 2 == 1 then
                    doTweenX('greatScrollMoveX'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.x') - greatScrollX, greatScrollTime, 'linear')
                    doTweenY('greatScrollMoveY'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.y') + greatScrollY, greatScrollTime, 'linear')
                else
                    doTweenX('greatScrollMoveX'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.x') + greatScrollX, greatScrollTime, 'linear')
                    doTweenY('greatScrollMoveY'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.y') - greatScrollY, greatScrollTime, 'linear')
                end
            end
        end
        runTimer('greatTextFlicker1', 0.1)
        runTimer('greatTextFlicker2', 0.2)
        runTimer('greatTextScroll', 2)
    end
    if tag == 'goodTextFlicker1' then
        for i = 1, 4 do
            setProperty('goodText'..i..'.alpha', 0)
        end
    end
    if tag == 'goodTextFlicker2' then
        for i = 1, 4 do
            setProperty('goodText'..i..'.alpha', 1)
        end
    end
    if tag == 'goodTextScroll' then
        for i = 1, 4 do
            doTweenY('goodTextUp'..i, 'goodText'..i, getProperty('goodText'..i..'.y') - 275, 4.5, 'linear')
        end
    end
    if tag == 'goodShow' then
        setProperty('superCoolResultsScreenBackgroundFlash.alpha', 0.6)
        doTweenAlpha('tWUWIAHDS', 'superCoolResultsScreenBackgroundFlash', 0, 0.3, 'linear')
        for i = 1, 4 do
            makeLuaSprite('goodText'..i, 'rankText/rankTextGOOD', 1235, -185 + (i * 275))
            setObjectCamera('goodText'..i, 'other')
            setObjectOrder('goodText'..i, getObjectOrder('resultsAnim') + 1)
            addLuaSprite('goodText'..i)
        end
        goodScrollX = 500
        goodScrollY = 26
        goodScrollTime = 50
        for i = 1, 4 do
            for j = 1, 9 do
                if themeColor == 'Default' then
                    makeLuaSprite('goodScroll'..j..i, 'rankText/rankScrollGOOD', - 600 + (i * goodScrollX), 85 + (j * 67) - (i-1)*goodScrollY)
                else
                    makeLuaSprite('goodScroll'..j..i, 'rankText/colorStuff/rankScrollGOOD-white', - 600 + (i * goodScrollX), 85 + (j * 67) - (i-1)*goodScrollY)
                    setProperty('goodScroll'..j..i..'.color', colorB)
                end
                setProperty('goodScroll'..j..i..'.angle', -3)
                setObjectCamera('goodScroll'..j..i, 'other')
                setObjectOrder('goodScroll'..j..i, getObjectOrder('superCoolResultsScreenBackground') + 1)
                addLuaSprite('goodScroll'..j..i)
                if j % 2 == 1 then
                    doTweenX('goodScrollMoveX'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.x') - goodScrollX, goodScrollTime, 'linear')
                    doTweenY('goodScrollMoveY'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.y') + goodScrollY, goodScrollTime, 'linear')
                else
                    doTweenX('goodScrollMoveX'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.x') + goodScrollX, goodScrollTime, 'linear')
                    doTweenY('goodScrollMoveY'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.y') - goodScrollY, goodScrollTime, 'linear')
                end
            end
        end
        runTimer('goodTextFlicker1', 0.1)
        runTimer('goodTextFlicker2', 0.2)
        runTimer('goodTextScroll', 2)
    end
end

function onTweenCompleted(tag)
    if tag == 'startUpThisShit' then
        runTimer('yoWait', 0.5)

        if char == 'pico' and accuracyNum == 100 then
            picoX = 19
            picoY = -70
            makeAnimatedLuaSprite('resultsAnim', 'results-pico/resultsPERFECT/perfectStart', picoX, picoY)
            addAnimationByPrefix('resultsAnim', 'resultsIntro', 'pico', 24, false)
            setObjectCamera('resultsAnim', 'other')
            setProperty('resultsAnim.visible', false)
            scaleObject('resultsAnim', 0.88, 0.88)
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsIntro', true)

            makeAnimatedLuaSprite('resultsAnim1', 'results-pico/resultsPERFECT/perfectLoop', picoX + 444, picoY - 61)
            addAnimationByPrefix('resultsAnim1', 'resultsLoop', 'pico', 24, true)
            setObjectCamera('resultsAnim1', 'other')
            setProperty('resultsAnim1.visible', false)
            scaleObject('resultsAnim1', 0.88, 0.88)
            setObjectOrder('resultsAnim1', getObjectOrder('resultsAnim') - 1)
            addLuaSprite('resultsAnim1', true)
            playAnim('resultsAnim1', 'resultsLoop', true)
        end
    end
    for i = 1, 4 do
        if tag == 'lossTextUp'..i then
            setProperty('lossText'..i..'.y', getProperty('lossText'..i..'.y') + 275)
            doTweenY('lossTextUp'..i, 'lossText'..i, getProperty('lossText'..i..'.y') - 275, 4, 'linear')
        end
        if tag == 'perfectTextUp'..i then
            setProperty('perfectText'..i..'.y', getProperty('perfectText'..i..'.y') + 464)
            doTweenY('perfectTextUp'..i, 'perfectText'..i, getProperty('perfectText'..i..'.y') - 464, 8, 'linear')
        end
        if tag == 'excellentTextUp'..i then
            setProperty('excellentText'..i..'.y', getProperty('excellentText'..i..'.y') + 590)
            doTweenY('excellentTextUp'..i, 'excellentText'..i, getProperty('excellentText'..i..'.y') - 590, 8, 'linear')
        end
        if tag == 'greatTextUp'..i then
            setProperty('greatText'..i..'.y', getProperty('greatText'..i..'.y') + 338)
            doTweenY('greatTextUp'..i, 'greatText'..i, getProperty('greatText'..i..'.y') - 338, 8, 'linear')
        end
        if tag == 'goodTextUp'..i then
            setProperty('goodText'..i..'.y', getProperty('goodText'..i..'.y') + 275)
            doTweenY('goodTextUp'..i, 'goodText'..i, getProperty('goodText'..i..'.y') - 275, 4, 'linear')
        end
    end
    for i = 1, 4 do
        for j = 1, 9 do
            if tag == 'lossScrollMoveX'..j..i then
                if j % 2 == 1 then
                    setProperty('lossScroll'..j..i..'.x', getProperty('lossScroll'..j..i..'.x') + lossScrollX)
                    setProperty('lossScroll'..j..i..'.y', getProperty('lossScroll'..j..i..'.y') - lossScrollY)
                    doTweenX('lossScrollMoveX'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.x') - lossScrollX, lossScrollTime, 'linear')
                    doTweenY('lossScrollMoveY'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.y') + lossScrollY, lossScrollTime, 'linear')
                else
                    setProperty('lossScroll'..j..i..'.x', getProperty('lossScroll'..j..i..'.x') - lossScrollX)
                    setProperty('lossScroll'..j..i..'.y', getProperty('lossScroll'..j..i..'.y') + lossScrollY)
                    doTweenX('lossScrollMoveX'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.x') + lossScrollX, lossScrollTime, 'linear')
                    doTweenY('lossScrollMoveY'..j..i, 'lossScroll'..j..i, getProperty('lossScroll'..j..i..'.y') - lossScrollY, lossScrollTime, 'linear')
                end
            end
            if tag == 'perfectScrollMoveX'..j..i then
                if j % 2 == 1 then
                    setProperty('perfectScroll'..j..i..'.x', getProperty('perfectScroll'..j..i..'.x') + perfectScrollX)
                    setProperty('perfectScroll'..j..i..'.y', getProperty('perfectScroll'..j..i..'.y') - perfectScrollY)
                    doTweenX('perfectScrollMoveX'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.x') - perfectScrollX, perfectScrollTime, 'linear')
                    doTweenY('perfectScrollMoveY'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.y') + perfectScrollY, perfectScrollTime, 'linear')
                else
                    setProperty('perfectScroll'..j..i..'.x', getProperty('perfectScroll'..j..i..'.x') - perfectScrollX)
                    setProperty('perfectScroll'..j..i..'.y', getProperty('perfectScroll'..j..i..'.y') + perfectScrollY)
                    doTweenX('perfectScrollMoveX'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.x') + perfectScrollX, perfectScrollTime, 'linear')
                    doTweenY('perfectScrollMoveY'..j..i, 'perfectScroll'..j..i, getProperty('perfectScroll'..j..i..'.y') - perfectScrollY, perfectScrollTime, 'linear')
                end
            end
            if tag == 'excellentScrollMoveX'..j..i then
                if j % 2 == 1 then
                    setProperty('excellentScroll'..j..i..'.x', getProperty('excellentScroll'..j..i..'.x') + excellentScrollX)
                    setProperty('excellentScroll'..j..i..'.y', getProperty('excellentScroll'..j..i..'.y') - excellentScrollY)
                    doTweenX('excellentScrollMoveX'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.x') - excellentScrollX, excellentScrollTime, 'linear')
                    doTweenY('excellentScrollMoveY'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.y') + excellentScrollY, excellentScrollTime, 'linear')
                else
                    setProperty('excellentScroll'..j..i..'.x', getProperty('excellentScroll'..j..i..'.x') - excellentScrollX)
                    setProperty('excellentScroll'..j..i..'.y', getProperty('excellentScroll'..j..i..'.y') + excellentScrollY)
                    doTweenX('excellentScrollMoveX'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.x') + excellentScrollX, excellentScrollTime, 'linear')
                    doTweenY('excellentScrollMoveY'..j..i, 'excellentScroll'..j..i, getProperty('excellentScroll'..j..i..'.y') - excellentScrollY, excellentScrollTime, 'linear')
                end
            end
            if tag == 'greatScrollMoveX'..j..i then
                if j % 2 == 1 then
                    setProperty('greatScroll'..j..i..'.x', getProperty('greatScroll'..j..i..'.x') + greatScrollX)
                    setProperty('greatScroll'..j..i..'.y', getProperty('greatScroll'..j..i..'.y') - greatScrollY)
                    doTweenX('greatScrollMoveX'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.x') - greatScrollX, greatScrollTime, 'linear')
                    doTweenY('greatScrollMoveY'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.y') + greatScrollY, greatScrollTime, 'linear')
                else
                    setProperty('greatScroll'..j..i..'.x', getProperty('greatScroll'..j..i..'.x') - greatScrollX)
                    setProperty('greatScroll'..j..i..'.y', getProperty('greatScroll'..j..i..'.y') + greatScrollY)
                    doTweenX('greatScrollMoveX'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.x') + greatScrollX, greatScrollTime, 'linear')
                    doTweenY('greatScrollMoveY'..j..i, 'greatScroll'..j..i, getProperty('greatScroll'..j..i..'.y') - greatScrollY, greatScrollTime, 'linear')
                end
            end
            if tag == 'goodScrollMoveX'..j..i then
                if j % 2 == 1 then
                    setProperty('goodScroll'..j..i..'.x', getProperty('goodScroll'..j..i..'.x') + goodScrollX)
                    setProperty('goodScroll'..j..i..'.y', getProperty('goodScroll'..j..i..'.y') - goodScrollY)
                    doTweenX('goodScrollMoveX'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.x') - goodScrollX, goodScrollTime, 'linear')
                    doTweenY('goodScrollMoveY'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.y') + goodScrollY, goodScrollTime, 'linear')
                else
                    setProperty('goodScroll'..j..i..'.x', getProperty('goodScroll'..j..i..'.x') - goodScrollX)
                    setProperty('goodScroll'..j..i..'.y', getProperty('goodScroll'..j..i..'.y') + goodScrollY)
                    doTweenX('goodScrollMoveX'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.x') + goodScrollX, goodScrollTime, 'linear')
                    doTweenY('goodScrollMoveY'..j..i, 'goodScroll'..j..i, getProperty('goodScroll'..j..i..'.y') - goodScrollY, goodScrollTime, 'linear')
                end
            end
        end
    end
    if tag == 'difficultyTextRSX' then
        setProperty('difficultyTextRS.x', getProperty('difficultyTextRS.x') + textMoveX)
        setProperty('difficultyTextRS.y', getProperty('difficultyTextRS.y') + textMoveY - 122)
        setProperty('cp1S.x', getProperty('cp1S.x') + textMoveX)
        setProperty('cp1S.y', getProperty('cp1S.y') + textMoveY - 122)
        setProperty('cpSL.x', getProperty('cpSL.x') + textMoveX)
        setProperty('cpSL.y', getProperty('cpSL.y') + textMoveY - 122)
        setProperty('cpSR.x', getProperty('cpSR.x') + textMoveX)
        setProperty('cpSR.y', getProperty('cpSR.y') + textMoveY - 122)
        setProperty('cpTS.x', getProperty('cpTS.x') + textMoveX)
        setProperty('cpTS.y', getProperty('cpTS.y') + textMoveY - 122)

        doTweenY('differDowners', 'difficultyTextRS', getProperty('difficultyTextRS.y') + 122, 0.3, 'quadOut')
        doTweenY('cp1SY', 'cp1S', getProperty('cp1S.y') + 122, 0.3, 'quadOut')
        doTweenY('cpSLY', 'cpSL', getProperty('cpSL.y') + 122, 0.3, 'quadOut')
        doTweenY('cpSRY', 'cpSR', getProperty('cpSR.y') + 122, 0.3, 'quadOut')
        doTweenY('cpTSY', 'cpTS', getProperty('cpTS.y') + 122, 0.3, 'quadOut')
        for i = 1, #nameSong do
            setProperty('songLetter'..i..'.x', getProperty('songLetter'..i..'.x') + textMoveX)
            setProperty('songLetter'..i..'.y', getProperty('songLetter'..i..'.y') + textMoveY - 122)
            doTweenY('moveLetter'..i, 'songLetter'..i, getProperty('songLetter'..i..'.y') + 122, 0.3, 'quadOut')
            if themeColor ~= 'Default' then
                setProperty('songLetterB'..i..'.x', getProperty('songLetterB'..i..'.x') + textMoveX)
                setProperty('songLetterB'..i..'.y', getProperty('songLetterB'..i..'.y') + textMoveY - 122)
                doTweenY('moveLetterB'..i, 'songLetterB'..i, getProperty('songLetterB'..i..'.y') + 122, 0.3, 'quadOut')
            end
        end
        runTimer('songNameMove', 3)
    end
    if tag == 'itsOverPal' then
        resultsOver = true
        endSong()
    end
end

function goodNoteHit(id, noteData, noteType, isSustainNote)
    local rating = getPropertyFromGroup('notes', id, 'rating')

    if rating == 'sick' then
        sicks = sicks + 1
    elseif rating == 'good' then
        goods = goods + 1
    elseif rating == 'bad' then
        bads = bads + 1
        if accuracyStyle == 'vslice' then
            setProperty('combo', 0)
        end
    elseif rating == 'shit' then
        shits = shits + 1
        if accuracyStyle == 'vslice' then
            setProperty('combo', 0)
        end
    end

    combo = getProperty('combo')
    if combo > maxCombo then
        maxCombo = combo
    end
end

function clamp(val)
    return math.max(0, math.min(255, val));
end

function rgbToHex(r, g, b)
    local r = math.floor(clamp(r or 0))
    local g = math.floor(clamp(g or 0))
    local b = math.floor(clamp(b or 0))
    local hex = string.format('0x%02X%02X%02X', r, g, b)
    return tonumber(hex)
end

function vsliceAccuracyCalc(total, s, g)
    if total == 0 then
        return 0;
    end
    return ((s + g) / total) * 100
end

function startAnims()
    if char == 'bf' then
        if accuracyNum == 100 then
            if naughtyness then
                introFrames = {}
                for i = 0, 136 do
                    table.insert(introFrames, i)
                end
                loopFrames = {}
                for i = 137, 148 do
                    table.insert(loopFrames, i)
                end
                makeFlxAnimateSprite('resultsAnim', 1340, 370)
                loadAnimateAtlas('resultsAnim', 'results-bf/resultsPERFECT')
                addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'boyfriend perfect rank', introFrames, 24, false)
                addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'boyfriend perfect rank', loopFrames, 24, true)
                setObjectCamera('resultsAnim', 'other')
                setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
                addLuaSprite('resultsAnim', true)
                playAnim('resultsAnim', 'resultsIntro', true)
                runTimer('perfectShow', 1.4)
                runTimer('resultsAnimLoop', 5.708333333)
                heartIntroFrames = {}
                for i = 0, 41 do
                    table.insert(heartIntroFrames, i)
                end
                heartLoopFrames = {}
                for i = 42, 115 do
                    table.insert(heartLoopFrames, i)
                end
                makeFlxAnimateSprite('hearts', 1340, 370)
                loadAnimateAtlas('hearts', 'results-bf/resultsPERFECT/hearts')
                addAnimationBySymbolIndices('hearts', 'heartsIntro', 'hearts full anim', heartIntroFrames, 24, false)
                addAnimationBySymbolIndices('hearts', 'heartsLoop', 'hearts full anim', heartLoopFrames, 24, true)
                setObjectCamera('hearts', 'other')
                setObjectOrder('hearts', getObjectOrder('resultsAnim') + 1)
                addLuaSprite('hearts', true)
                setProperty('hearts.visible', false)
                playAnim('hearts', 'heartsIntro', true)
                runTimer('heartIntro', 4.67)
            else
                introFrames = {}
                for i = 150, 235 do
                    table.insert(introFrames, i)
                end
                loopFrames = {}
                for i = 236, 246 do
                    table.insert(loopFrames, i)
                end
                makeFlxAnimateSprite('resultsAnim', 1340, 370)
                loadAnimateAtlas('resultsAnim', 'results-bf/resultsPERFECT')
                addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'boyfriend perfect rank', introFrames, 24, false)
                addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'boyfriend perfect rank', loopFrames, 24, true)
                setObjectCamera('resultsAnim', 'other')
                setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
                addLuaSprite('resultsAnim', true)
                playAnim('resultsAnim', 'resultsIntro', true)
                runTimer('perfectShow', 1.4)
                runTimer('resultsAnimLoop', 3.583333333)
                makeAnimatedLuaSprite('tickleFight', 'results-bf/resultsPERFECT/tickleFight/tickleFight', 605, 360)
                addAnimationByPrefix('tickleFight', 'tickleFightIntro', 'tick fight intro', 24, false)
                addAnimationByPrefix('tickleFight', 'tickleFightLoop', 'tickle fight loop', 24, true)
                setObjectCamera('tickleFight', 'other')
                scaleObject('tickleFight', 0.6, 0.6)
                setObjectOrder('tickleFight', getObjectOrder('resultsAnim') + 1)
                addLuaSprite('tickleFight', true)
                setProperty('tickleFight.visible', false)
                playAnim('tickleFight', 'tickleFightIntro', true)
                runTimer('tickleFightIntro', 4.67)
            end
        elseif accuracyNum > 89 and accuracyNum < 100 then
            introFrames = {}
            for i = 0, 27 do
                table.insert(introFrames, i)
            end
            loopFrames = {}
            for i = 28, 259 do
                table.insert(loopFrames, i)
            end
            makeFlxAnimateSprite('resultsAnim', 1330, 430)
            loadAnimateAtlas('resultsAnim', 'results-bf/resultsEXCELLENT')
            addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'bf results excellent', introFrames, 24, false)
            addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'bf results excellent', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('excellentShow', 1.1)
            runTimer('resultsAnimLoop', 1.166666667)
        elseif accuracyNum > 79 and accuracyNum < 90 then
            introFramesGF = {}
            for i = 0, 7 do
                table.insert(introFramesGF, i)
            end
            loopFramesGF = {}
            for i = 8, 43 do
                table.insert(loopFramesGF, i)
            end
            makeFlxAnimateSprite('resultsGF', 820, 327)
            if themeColor == 'Default' then
                loadAnimateAtlas('resultsGF', 'results-bf/resultsGREAT/gf')
                setObjectOrder('resultsGF', getObjectOrder('cpSL') - 1)
            else
                loadAnimateAtlas('resultsGF', 'results-bf/resultsGREAT/gf/colorStuff/base')
                makeAnimatedLuaSprite('resultsGFW', 'results-bf/resultsGREAT/gf/colorStuff/white/spritesheet', 622, -122)
                loadAnimateAtlas('resultsGFW', 'results-bf/resultsGREAT/gf/colorStuff/white')
                addAnimation('resultsGFW', 'resultsIntro', introFramesGF, 24, false)
                addAnimation('resultsGFW', 'resultsLoop', loopFramesGF, 24, true)
                setObjectCamera('resultsGFW', 'other')
                setObjectOrder('resultsGFW', getObjectOrder('cpSL') - 1)
                setProperty('resultsGFW.color', color)
                setProperty('resultsGFW.alpha', 0.5)
                setProperty('resultsGFW.visible', false)
                addLuaSprite('resultsGFW', true)

                setObjectOrder('resultsGF', getObjectOrder('resultsGFW') - 1)
            end
            addAnimationBySymbolIndices('resultsGF', 'resultsIntro', 'gf jumping', introFramesGF, 24, false)
            addAnimationBySymbolIndices('resultsGF', 'resultsLoop', 'gf jumping', loopFramesGF, 24, true)
            setObjectCamera('resultsGF', 'other')
            setProperty('resultsGF.visible', false)
            addLuaSprite('resultsGF', true)
            runTimer('resultsGF', 0.3)

            introFrames = {}
            for i = 0, 13 do
                table.insert(introFrames, i)
            end
            loopFrames = {}
            for i = 14, 38 do
                table.insert(loopFrames, i)
            end
            makeFlxAnimateSprite('resultsAnim', 930, 357)
            loadAnimateAtlas('resultsAnim', 'results-bf/resultsGREAT/bf')
            addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'bf jumping ', introFrames, 24, false)
            addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'bf jumping ', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpSL') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('greatShow', 0.5)
            runTimer('resultsAnimLoop', 0.5416666667)
        elseif accuracyNum > 59 and accuracyNum < 80 then
            introFramesGF = {}
            for i = 0, 45 do
                table.insert(introFramesGF, i)
            end
            loopFramesGF = {}
            for i = 46, 51 do
                table.insert(loopFramesGF, i)
            end
            if themeColor == 'Default' then
                makeAnimatedLuaSprite('resultsGF', 'results-bf/resultsGOOD/resultGirlfriendGOOD', 630, 330)
                setObjectOrder('resultsGF', getObjectOrder('cpTS') - 1)
            else
                makeAnimatedLuaSprite('resultsGF', 'results-bf/resultsGOOD/colorStuff/resultGirlfriendGOOD-base', 630, 330)
                makeAnimatedLuaSprite('resultsGFW', 'results-bf/resultsGOOD/colorStuff/resultGirlfriendGOOD-white', 630, 330)
                addAnimation('resultsGFW', 'resultsIntro', introFramesGF, 24, false)
                addAnimation('resultsGFW', 'resultsLoop', loopFramesGF, 24, true)
                setObjectCamera('resultsGFW', 'other')
                setProperty('resultsGFW.color', color)
                setProperty('resultsGFW.alpha', 0.5)
                setObjectOrder('resultsGFW', getObjectOrder('cpTS') - 1)
                addLuaSprite('resultsGFW', true)
                playAnim('resultsGFW', 'resultsIntro', true)

                setObjectOrder('resultsGF', getObjectOrder('resultsGFW') - 1)
            end
            addAnimation('resultsGF', 'resultsIntro', introFramesGF, 24, false)
            addAnimation('resultsGF', 'resultsLoop', loopFramesGF, 24, true)
            setObjectCamera('resultsGF', 'other')
            addLuaSprite('resultsGF', true)
            playAnim('resultsGF', 'resultsIntro', true)
            runTimer('resultsGFLoop', 1.875)
            introFrames = {}
            for i = 0, 69 do
                table.insert(introFrames, i)
            end
            loopFrames = {}
            for i = 70, 73 do
                table.insert(loopFrames, i)
            end
            makeAnimatedLuaSprite('resultsAnim', 'results-bf/resultsGOOD/resultBoyfriendGOOD', 650, -160)
            addAnimation('resultsAnim', 'resultsIntro', introFrames, 24, false)
            addAnimation('resultsAnim', 'resultsLoop', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            scaleObject('resultsAnim', 0.95, 0.95)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('goodShow', 0.5)
            runTimer('resultsAnimLoop', 2.875)
        elseif accuracyNum < 60 then
            introFrames = {}
            for i = 0, 148 do
                table.insert(introFrames, i)
            end
            loopFrames = {}
            for i = 149, 318 do
                table.insert(loopFrames, i)
            end
            makeFlxAnimateSprite('resultsAnim', 640, 380)
            loadAnimateAtlas('resultsAnim', 'results-bf/resultsSHIT')
            addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'LOSS Animation', introFrames, 24, false)
            addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'LOSS Animation', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('lossShow', 3.8)
            runTimer('resultsAnimLoop', 6.166666667)
        end
    elseif char == 'pico' then
        if accuracyNum == 100 then
            setProperty('resultsAnim.visible', true)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('perfectShow', 2)
            runTimer('perfectPicoAnimLoop', 3.166666667)
        elseif accuracyNum > 89 and accuracyNum < 100 then
            introFrames = {}
            for i = 0, 33 do
                table.insert(introFrames, i)
            end
            loopFrames = {}
            for i = 34, 176 do
                table.insert(loopFrames, i)
            end
            makeFlxAnimateSprite('resultsAnim', 830, 420)
            loadAnimateAtlas('resultsAnim', 'results-pico/resultsGREAT')
            addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'pico great rank', introFrames, 24, false)
            addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'pico great rank', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('excellentShow', 0.5)
            runTimer('resultsAnimLoop', 1.416666667)
        elseif accuracyNum > 79 and accuracyNum < 90 then
            introFrames = {}
            for i = 0, 33 do
                table.insert(introFrames, i)
            end
            loopFrames = {}
            for i = 34, 176 do
                table.insert(loopFrames, i)
            end
            makeFlxAnimateSprite('resultsAnim', 830, 420)
            loadAnimateAtlas('resultsAnim', 'results-pico/resultsGREAT')
            addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'pico great rank', introFrames, 24, false)
            addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'pico great rank', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsIntro', true)
            runTimer('greatShow', 0.5)
            runTimer('resultsAnimLoop', 1.416666667)
        elseif accuracyNum > 59 and accuracyNum < 80 then
            coolNumber = math.random(1, 12)
            if coolNumber < 11 then
                introFrames = {}
                for i = 0, 40 do
                    table.insert(introFrames, i)
                end
                loopFrames = {}
                for i = 41, 215 do
                    table.insert(loopFrames, i)
                end
                makeFlxAnimateSprite('resultsAnim', 830, 420)
                loadAnimateAtlas('resultsAnim', 'results-pico/resultsGOOD')
                addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'pico good placeholder', introFrames, 24, false)
                addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'pico good placeholder', loopFrames, 24, true)
                setObjectCamera('resultsAnim', 'other')
                setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
                addLuaSprite('resultsAnim', true)
                playAnim('resultsAnim', 'resultsIntro', true)
                runTimer('goodShow', 0.5)
                runTimer('resultsAnimLoop', 1.708333333)
            elseif coolNumber == 12 then
                introFrames = {}
                for i = 633, 848 do
                    table.insert(introFrames, i)
                end
                loopFrames = {}
                for i = 41, 215 do
                    table.insert(loopFrames, i)
                end
                makeFlxAnimateSprite('resultsAnim', 830, 420)
                loadAnimateAtlas('resultsAnim', 'results-pico/resultsGOOD')
                addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'pico good placeholder', introFrames, 24, false)
                addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'pico good placeholder', loopFrames, 24, true)
                setObjectCamera('resultsAnim', 'other')
                setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
                addLuaSprite('resultsAnim', true)
                playAnim('resultsAnim', 'resultsIntro', true)
                runTimer('goodShow', 0.5)
                runTimer('resultsAnimLoop', 9)
            else
                introFrames = {}
                for i = 216, 631 do
                    table.insert(introFrames, i)
                end
                loopFrames = {}
                for i = 41, 215 do
                    table.insert(loopFrames, i)
                end
                makeFlxAnimateSprite('resultsAnim', 830, 420)
                loadAnimateAtlas('resultsAnim', 'results-pico/resultsGOOD')
                addAnimationBySymbolIndices('resultsAnim', 'resultsIntro', 'pico good placeholder', introFrames, 24, false)
                addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'pico good placeholder', loopFrames, 24, true)
                setObjectCamera('resultsAnim', 'other')
                setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
                addLuaSprite('resultsAnim', true)
                playAnim('resultsAnim', 'resultsIntro', true)
                runTimer('goodShow', 0.5)
                runTimer('resultsAnimLoop', 17.33333333)
            end
        elseif accuracyNum < 60 then
            loopFrames = {}
            for i = 0, 173 do
                table.insert(loopFrames, i)
            end
            makeFlxAnimateSprite('resultsAnim', 770, 415)
            loadAnimateAtlas('resultsAnim', 'results-pico/resultsSHIT')
            addAnimationBySymbolIndices('resultsAnim', 'resultsLoop', 'pico loss rank', loopFrames, 24, true)
            setObjectCamera('resultsAnim', 'other')
            setObjectOrder('resultsAnim', getObjectOrder('cpTS') - 1)
            addLuaSprite('resultsAnim', true)
            playAnim('resultsAnim', 'resultsLoop', true)
            runTimer('lossShow', 3.75)
        end
    end
end