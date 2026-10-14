package;

/** Gameplay lifecycle points that more than one source script engine hears. */
enum abstract SourceLifecycleEvent(String) to String {
	var GameOver = 'GameOver';
	var RecalculateRating = 'RecalculateRating';
	var Pause = 'Pause';
	var EndSong = 'EndSong';
	var UpdateScoreBar = 'UpdateScoreBar';
	var PreUpdateScore = 'PreUpdateScore';
	var UpdateScore = 'UpdateScore';
	var CountdownStarted = 'CountdownStarted';
	var StartCountdownAgain = 'StartCountdownAgain';
	var CreatePost = 'CreatePost';
	var SongStart = 'SongStart';
	var StepHit = 'StepHit';
}
