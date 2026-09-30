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
