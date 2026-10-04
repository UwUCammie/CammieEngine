package;

/** Pure source health magnitudes for Psych and Nightmare Vision note play. */
class SourceHealthDelta {
	static inline var PSYCH_HIT_HEALTH:Float = 0.02;
	static inline var PSYCH_MISS_HEALTH:Float = 0.1;
	static inline var PSYCH_PRESS_MISS_DAMAGE:Float = 0.05;
	static inline var NIGHTMARE_HIT_HEALTH:Float = 0.023;
	static inline var NIGHTMARE_MISS_HEALTH:Float = 0.0475;
	static inline var PRESS_MISS_DAMAGE:Float = 0.05;

	/**
	 * Return the source hit-health amount before the caller chooses its sign.
	 * The owner factor is Psych/NV's healthGain setting. The native modifier
	 * factor is applied separately so ignoreHealthMods can pass 1 without
	 * discarding the source gameplay setting.
	 */
	public static function hit(nightmareVision:Bool, authoredHealth:Null<Float>,
		ownerFactor:Float = 1, nativeModifierFactor:Float = 1,
		isSustain:Bool = false, holdSubdivisions:Int = 1,
		psychGuitarHeroSustains:Bool = false):Float {
		if (!nightmareVision && isSustain && psychGuitarHeroSustains) return 0;

		var amount = authoredHealth == null
			? (nightmareVision ? NIGHTMARE_HIT_HEALTH : PSYCH_HIT_HEALTH)
			: authoredHealth;
		amount *= ownerFactor * nativeModifierFactor;
		if (nightmareVision && isSustain) amount /= holdSubdivisions;
		return amount;
	}

	/** Return one source note-miss damage amount before the caller subtracts it. */
	public static function miss(nightmareVision:Bool, authoredHealth:Null<Float>,
		ownerFactor:Float = 1, nativeModifierFactor:Float = 1,
		isSustain:Bool = false, holdSubdivisions:Int = 1):Float {
		var amount = authoredHealth == null
			? (nightmareVision ? NIGHTMARE_MISS_HEALTH : PSYCH_MISS_HEALTH)
			: authoredHealth;
		amount *= ownerFactor * nativeModifierFactor;
		if (nightmareVision && isSustain) amount /= holdSubdivisions;
		return amount;
	}

	/** Empty-keypress damage has no Note, so no per-note native modifier applies. */
	public static function pressMiss(ownerFactor:Float = 1,
		?psychPressMissDamage:Null<Float>):Float {
		var amount = psychPressMissDamage == null
			? PRESS_MISS_DAMAGE : psychPressMissDamage;
		return amount * ownerFactor;
	}
}
