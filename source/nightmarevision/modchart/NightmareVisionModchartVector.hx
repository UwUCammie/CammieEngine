package nightmarevision.modchart;

#if flixel
import flixel.util.FlxPool;
#end

// modified from lime.math.Vector4
/**
	`NightmareVisionModchartVector` is a vector suitable for three-dimensional
	math, containing (x, y, z) components
**/
#if !lime_debug
@:fileXml('tags="haxe,release"')
@:noDebug
#end
@:keep
class NightmareVisionModchartVector #if flixel implements IFlxPooled #end
{
	#if flixel
	static final _pool = new FlxPool<NightmareVisionModchartVector>(() -> new NightmareVisionModchartVector());
	#else
	static final _pool = new NightmareVisionVectorPool();
	#end

	public static function get(x:Float = 0, y:Float = 0, z:Float = 0):NightmareVisionModchartVector
	{
		return _pool.get().setTo(x, y, z);
	}

	public static inline function recycle(x:Float = 0, y:Float = 0, z:Float = 0):NightmareVisionModchartVector
	{
		return _pool.get().setTo(x, y, z);
	}

	public inline function put():Void
	{
		setTo(0, 0, 0);
		_pool.put(this);
	}

	// should set this up weak vecs later
	var _weak:Bool = false;

	public inline function putWeak() {}

	public function destroy():Void {}

	/**
		A constant representing the x axis (1, 0, 0)
	**/
	public static var X_AXIS(get, never):NightmareVisionModchartVector;

	/**
		A constant representing the y axis (0, 1, 0)
	**/
	public static var Y_AXIS(get, never):NightmareVisionModchartVector;

	/**
		A constant representing the z axis (0, 0, 1)
	**/
	public static var Z_AXIS(get, never):NightmareVisionModchartVector;

	/**
		Get the length of this vector
	**/
	public var length(get, never):Float;

	/**
		Get the squared length of this vector
		(avoiding the use of `Math.sqrt` for faster
		performance)
	**/
	public var lengthSquared(get, never):Float;

	/**
		The x component value
	**/
	public var x:Float;

	/**
		The y component value
	**/
	public var y:Float;

	/**
		The z component value
	**/
	public var z:Float;

	/**
		Creates a new `NightmareVisionModchartVector` instance
		@param	x	(Optional) An initial x value (default is 0)
		@param	y	(Optional) An initial y value (default is 0)
		@param	z	(Optional) An initial z value (default is 0)
	**/
	public function new(x:Float = 0.0, y:Float = 0.0, z:Float = 0.0)
	{
		setTo(x, y, z);
	}

	/**
		Adds two `NightmareVisionModchartVector` instances together and returns the result
		@param	a	A `NightmareVisionModchartVector` instance to add to the current one
		@param	result	(Optional) A `NightmareVisionModchartVector` instance to store the result
		@return	A `NightmareVisionModchartVector` instance with the added value
	**/
	public inline function add(a:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
		result.setTo(this.x + a.x, this.y + a.y, this.z + a.z);
		return result;
	}

	/**
		Calculates the angle between two `NightmareVisionModchartVector` coordinates
		@param	a	A `NightmareVisionModchartVector` instance
		@param	b	A second `NightmareVisionModchartVector` instance
		@return	The calculated angle
	**/
	public static inline function angleBetween(a:NightmareVisionModchartVector, b:NightmareVisionModchartVector):Float
	{
		var a0 = a.clone();
		a0.normalize();
		var b0 = b.clone();
		b0.normalize();

		return Math.acos(a0.dotProduct(b0));
	}

	/**
		Creates a new `NightmareVisionModchartVector` instance with the same values as the current one
		@return	A new `NightmareVisionModchartVector` instance with the same values
	**/
	public inline function copy():NightmareVisionModchartVector return new NightmareVisionModchartVector(x, y, z);

	public inline function clone():NightmareVisionModchartVector
	{
		return NightmareVisionModchartVector.get(x, y, z);
	}

	/**
		Creates a new `NightmareVisionModchartVector` instance linearly interpolated between this NightmareVisionModchartVector and the given goal by the given alpha
		@param goal A `NightmareVisionModchartVector` instance to interpolate towards
		@param alpha How far the interpolation is
		@return A `NightmareVisionModchartVector instance linearly interpolated`
	**/
	// https://gamedev.stackexchange.com/questions/18615/how-do-i-linearly-interpolate-between-two-vectors
	public function lerp(goal:NightmareVisionModchartVector, alpha:Float):NightmareVisionModchartVector
	{
		return NightmareVisionModchartVector.get(alpha * goal.x + x * (1 - alpha), alpha * goal.y + y * (1 - alpha), alpha * goal.z + z * (1 - alpha));
	}

	/**
		Copies the x, y and z component values of another `NightmareVisionModchartVector` instance
		@param	sourceNightmareVisionModchartVector	A `NightmareVisionModchartVector` instance to copy from
	**/
	public inline function copyFrom(sourceNightmareVisionModchartVector:NightmareVisionModchartVector):Void
	{
		x = sourceNightmareVisionModchartVector.x;
		y = sourceNightmareVisionModchartVector.y;
		z = sourceNightmareVisionModchartVector.z;
	}

	/**
		Performs vector multiplication between this vector and another `NightmareVisionModchartVector` instance
		@param	A `NightmareVisionModchartVector` instance to multiply by
		@param	result(Optional) A `NightmareVisionModchartVector` to use for the result
		@return	A `NightmareVisionModchartVector` instance with the result
		@see https://en.wikipedia.org/wiki/Cross_product
	**/
	public inline function crossProduct(a:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
		result.setTo(y * a.z - z * a.y, z * a.x - x * a.z, x * a.y - y * a.x);
		return result;
	}

	/**
		Decrements the x, y and z component values by those in another `NightmareVisionModchartVector` instance
		@param	a	A `NightmareVisionModchartVector` instance to decrement the current vector by
	**/
	public inline function decrementBy(a:NightmareVisionModchartVector):Void
	{
		x -= a.x;
		y -= a.y;
		z -= a.z;
	}

	/**
		Calculates the distance between two vectors
		@param	pt1	A `NightmareVisionModchartVector` instance
		@param	pt2	A second `NightmareVisionModchartVector` instance
		@return	The distance between each vector
	**/
	public inline static function distance(pt1:NightmareVisionModchartVector, pt2:NightmareVisionModchartVector):Float
	{
		var x = pt2.x - pt1.x;
		var y = pt2.y - pt1.y;
		var z = pt2.z - pt1.z;

		return Math.sqrt(x * x + y * y + z * z);
	}

	/**
		Calculates the squared distance between two vectors,
		(avoids the use of `Math.sqrt` for faster performance)
		@param	pt1	A `NightmareVisionModchartVector` instance
		@param	pt2	A second `NightmareVisionModchartVector` instance
		@return	The square of the distance between each vector
	**/
	public inline static function distanceSquared(pt1:NightmareVisionModchartVector, pt2:NightmareVisionModchartVector):Float
	{
		var x = pt2.x - pt1.x;
		var y = pt2.y - pt1.y;
		var z = pt2.z - pt1.z;

		return x * x + y * y + z * z;
	}

	/**
		Calculates the dot product of the current vector with another `NightmareVisionModchartVector` instance
		@param	a	A `NightmareVisionModchartVector` instance to use in the dot product
		@return	The calculated dot product value
		@see https://en.wikipedia.org/wiki/Dot_product
	**/
	public inline function dotProduct(a:NightmareVisionModchartVector):Float
	{
		return x * a.x + y * a.y + z * a.z;
	}

	/**
		Whether two `NightmareVisionModchartVector` instances have equal component values.

		Comparing the w component value is optional.
		@param	toCompare	A `NightmareVisionModchartVector` instance to compare against
		@return	Whether both instances have equal values
	**/
	public inline function equals(toCompare:NightmareVisionModchartVector):Bool
	{
		return x == toCompare.x && y == toCompare.y && z == toCompare.z;
	}

	/**
		Increments the x, y and z component values by those in a second `NightmareVisionModchartVector` instance
		@param	a	A `NightmareVisionModchartVector` instance to increment the current vector by
	**/
	public inline function incrementBy(a:NightmareVisionModchartVector):Void
	{
		x += a.x;
		y += a.y;
		z += a.z;
	}

	/**
		Whether two `NightmareVisionModchartVector` instances have nearly equal component values.
		Comparison is performed within a given tolerance value.
		@param	toCompare	A `NightmareVisionModchartVector` instance to compare against
		@param	tolerance	A floating point value determining how near the values must be to be considered near equal
		@return	Whether both instances have equal values, within the given tolerance
	**/
	public inline function nearEquals(toCompare:NightmareVisionModchartVector, tolerance:Float):Bool
	{
		return Math.abs(x - toCompare.x) < tolerance && Math.abs(y - toCompare.y) < tolerance && Math.abs(z - toCompare.z) < tolerance;
	}

	/**
		Negates the x, y and z values of the current vector
		(multiplying each value by -1)
	**/
	public inline function negate():Void
	{
		x *= -1;
		y *= -1;
		z *= -1;
	}

	/**
		Divides the x, y and z component values by the
		length of the vector
	**/
	public inline function normalize():Float
	{
		var l = length;

		if (l != 0)
		{
			x /= l;
			y /= l;
			z /= l;
		}

		return l;
	}

	/**
	    Projects this vector onto another `NightmareVisionModchartVector` instance
	    @param onto A `NightmareVisionModchartVector` instance to project onto
	    @param result (Optional) A `NightmareVisionModchartVector` instance to store the result
	    @return A `NightmareVisionModchartVector` instance containing the projected vector
		@see https://en.wikipedia.org/wiki/Vector_projection
	**/
	public inline function project(onto:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
	    var scalar = dotProduct(onto) / onto.lengthSquared;
	    result.setTo(onto.x * scalar, onto.y * scalar, onto.z * scalar);
	    return result;
	}

	/**
		Projects this vector onto a plane defined by a normal `NightmareVisionModchartVector`
		@param normal A `NightmareVisionModchartVector` instance representing the plane's normal (should be normalized)
		@param result (Optional) A `NightmareVisionModchartVector` instance to store the result
		@return A `NightmareVisionModchartVector` instance containing the projected vector
		@see https://en.wikipedia.org/wiki/Vector_projection
	**/
	public inline function projectOntoPlane(normal:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
	    var projected = project(normal, NightmareVisionModchartVector.get());
	    result.setTo(x - projected.x, y - projected.y, z - projected.z);
	    projected.put();
	    return result;
	}
	/**
		Puts this vector's values on an Absolute Value.
		@param result (Optional) A `NightmareVisionModchartVector` instance to store the result
		@return A `Vector` instance containing the value in absolute.
	**/
	public inline function abs(result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
		result ??= NightmareVisionModchartVector.get();
		result.setTo(Math.abs(x), Math.abs(y), Math.abs(z));
		return result;
	}
	/**
		Scales the x, y and z component values by a scale value
		@param	s	The amount of scale to apply
	**/
	public inline function scaleBy(s:Float):Void
	{
		x *= s;
		y *= s;
		z *= s;
	}

	/**
		Sets the x, y and z component values
		@param	xa	An x value
		@param	ya	A y value
		@param	za	A z value

		@return returns `this` vector3
	**/
	public inline function setTo(xa:Float, ya:Float, za:Float):NightmareVisionModchartVector
	{
		x = xa;
		y = ya;
		z = za;

		return this;
	}
	/**
		Subtracts the values of a second `NightmareVisionModchartVector` instance
		from the current one
		@param	a	A second `NightmareVisionModchartVector` instance to substract
		@param	result	(Optional) A `NightmareVisionModchartVector` instance to store the result
		@return	A `NightmareVisionModchartVector` instance containing the subtracted value
	**/
	public inline function subtract(a:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
		result.setTo(x - a.x, y - a.y, z - a.z);
		return result;
	}

	/**
	    Creates a `NightmareVisionModchartVector` from spherical coordinates
	    @param theta The polar angle in radians (from the z axis)
	    @param phi The azimuthal angle in radians (from the x axis)
	    @return A normalized `NightmareVisionModchartVector` instance
		@see https://en.wikipedia.org/wiki/Spherical_coordinate_system
	**/
	public static inline function fromAngle(theta:Float, phi:Float):NightmareVisionModchartVector
	{
	    var sinTheta = Math.sin(theta);
	    return NightmareVisionModchartVector.get(sinTheta * Math.cos(phi), sinTheta * Math.sin(phi), Math.cos(theta));
	}

	/**
	    Returns a component-wise minimum of two `NightmareVisionModchartVector` instances
	    @param a A `NightmareVisionModchartVector` instance
	    @param b A second `NightmareVisionModchartVector` instance
	    @param result (Optional) A `NightmareVisionModchartVector` instance to store the result
	    @return A `NightmareVisionModchartVector` instance with the minimum values
	**/
	public static inline function min(a:NightmareVisionModchartVector, b:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
	    result.setTo(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.min(a.z, b.z));
	    return result;
	}

	/**
	    Returns a component-wise maximum of two `NightmareVisionModchartVector` instances
	    @param a A `NightmareVisionModchartVector` instance
	    @param b A second `NightmareVisionModchartVector` instance
	    @param result (Optional) A `NightmareVisionModchartVector` instance to store the result
	    @return A `NightmareVisionModchartVector` instance with the maximum values
	**/
	public static inline function max(a:NightmareVisionModchartVector, b:NightmareVisionModchartVector, result:NightmareVisionModchartVector = null):NightmareVisionModchartVector
	{
	    result ??= NightmareVisionModchartVector.get();
	    result.setTo(Math.max(a.x, b.x), Math.max(a.y, b.y), Math.max(a.z, b.z));
	    return result;
	}


	@:dox(hide) public inline function toString():String
	{
		return "NightmareVisionModchartVector(" + x + ", " + y + ", " + z + ")";
	}

	// Getters & Setters
	@:noCompletion private inline function get_length():Float
	{
		return Math.sqrt(x * x + y * y + z * z);
	}

	@:noCompletion private inline function get_lengthSquared():Float
	{
		return x * x + y * y + z * z;
	}

	private inline static function get_X_AXIS():NightmareVisionModchartVector
	{
		return NightmareVisionModchartVector.get(1, 0, 0);
	}

	private inline static function get_Y_AXIS():NightmareVisionModchartVector
	{
		return NightmareVisionModchartVector.get(0, 1, 0);
	}

	private inline static function get_Z_AXIS():NightmareVisionModchartVector
	{
		return NightmareVisionModchartVector.get(0, 0, 1);
	}
}

#if !flixel
private class NightmareVisionVectorPool {
 var free:Array<NightmareVisionModchartVector> = [];
 public function new() {}
 public function get():NightmareVisionModchartVector return free.length == 0 ? new NightmareVisionModchartVector() : free.pop();
 public function put(v:NightmareVisionModchartVector):Void { if (free.indexOf(v) < 0) free.push(v); }
}
#end
