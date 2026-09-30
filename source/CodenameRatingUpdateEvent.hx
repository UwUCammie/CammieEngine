package;

/** Mutable onRatingUpdate event, in the donor's recycle field order. */
@:keep
class CodenameRatingUpdateEvent extends CodenameGameEvent {
	public var rating:Null<CodenameComboRating>;
	public var oldRating:Null<CodenameComboRating>;

	public function new(?rating:CodenameComboRating, ?oldRating:CodenameComboRating) {
		super();
		recycle(rating, oldRating);
	}

	public function recycle(rating:Null<CodenameComboRating>,
		oldRating:Null<CodenameComboRating>):CodenameRatingUpdateEvent {
		recycleBase();
		this.rating = rating;
		this.oldRating = oldRating;
		return this;
	}
}
