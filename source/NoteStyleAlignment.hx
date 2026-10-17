package;

/** Render-space horizontal centering for imported note-style atlases. */
class NoteStyleAlignment {
	// FunkinCrew/Funkin Strumline: STRUMLINE_SIZE=104, INITIAL_OFFSET=-.275*104,
	// NUDGE=2. buildNoteSprite centers notes on 104 and subtracts NUDGE;
	// receptors start at INITIAL_OFFSET and add the style's strumline offsets.
	static inline var VSLICE_LANE_SIZE:Float = 104;
	static inline var VSLICE_INITIAL_OFFSET:Float = -0.275 * VSLICE_LANE_SIZE;
	static inline var VSLICE_NOTE_NUDGE:Float = 2;

	/** Map donor receptor X to this fork's 112px note lane. Donor
	 * StrumlineNote.updateHitbox runs once before playStatic, so its hitbox
	 * width stays fixed while centerOffsets changes with animation frames. */
	public static function vSliceReceptorOffsetX(width:Float, originX:Float, scaleX:Float,
		laneWidth:Float, styleX:Float, anchorWidth:Float):Float {
		var donorNoteCenter = VSLICE_LANE_SIZE / 2 - VSLICE_NOTE_NUDGE;
		var donorReceptorCenter = VSLICE_INITIAL_OFFSET + styleX + anchorWidth / 2;
		return centeredOffsetX(width, originX, scaleX, laneWidth,
			donorNoteCenter - donorReceptorCenter);
	}

	/** The donor puts a note at y - INITIAL_OFFSET on its hit beat, while the
	 * receptor starts at y + styleY. This fork puts the note at y, so preserve
	 * their relative vertical positions when mapping receptor frames. */
	public static function vSliceReceptorOffsetY(height:Float, originY:Float, scaleY:Float,
		laneHeight:Float, styleY:Float, anchorHeight:Float):Float {
		var hostReceptorCenter = VSLICE_INITIAL_OFFSET + styleY + anchorHeight / 2;
		return centeredOffsetY(height, originY, scaleY, laneHeight,
			laneHeight / 2 - hostReceptorCenter);
	}

	/** Where a donor note splash's centre lies from its receptor's centre, horizontally.
	 * The donor puts the splash at its lane plus the style's splash offset and draws it 0.3 of
	 * its width to the left, and the receptor at the same lane plus the strumline offset, so the
	 * lane's own start cancels. A style authors the two offsets so the splash looks centred. */
	public static function vSliceSplashCenterX(splashWidth:Float, splashOffsetX:Float, strumlineOffsetX:Float,
		receptorAnchorWidth:Float):Float {
		return splashOffsetX - strumlineOffsetX + 0.2 * splashWidth - receptorAnchorWidth / 2;
	}

	/** The vertical counterpart. The donor lifts the splash by INITIAL_OFFSET while the receptor only
	 * takes its strumline offset, which is why this carries that term and the horizontal one does not. */
	public static function vSliceSplashCenterY(splashHeight:Float, splashOffsetY:Float, strumlineOffsetY:Float,
		receptorAnchorHeight:Float):Float {
		return -VSLICE_INITIAL_OFFSET + splashOffsetY - strumlineOffsetY + 0.2 * splashHeight - receptorAnchorHeight / 2;
	}

	public static function centeredOffsetX(width:Float, originX:Float, scaleX:Float,
		laneWidth:Float, authoredOffsetX:Float):Float {
		// FlxSprite.getGraphicBounds() starts at
		// x + origin.x - offset.x - origin.x * scale.x. Set the offset so the
		// full Sparrow frame canvas is centered on the receptor lane. Trimmed
		// subtextures retain their authored frameX within that canvas.
		return originX * (1 - scaleX) + (width - laneWidth) / 2 + authoredOffsetX;
	}

	/** Vertical counterpart used by receptor atlases whose frame canvases vary
	 * between static, press, and confirm animations. */
	public static function centeredOffsetY(height:Float, originY:Float, scaleY:Float,
		laneHeight:Float, authoredOffsetY:Float):Float {
		return originY * (1 - scaleY) + (height - laneHeight) / 2 + authoredOffsetY;
	}
}
