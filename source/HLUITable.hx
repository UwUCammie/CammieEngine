package;

import flixel.FlxG;
import flixel.util.FlxColor;

@:keep
class HLUITableRow extends HLUIBox {
	public var labels:Array<HLUILabel> = [];
	public var index:Int = 0;
	public var onRelease:Null<Void->Void>;
	public var table:Null<HLUITable>;
	var pressed:Bool = false;

	public function new(index:Int) {
		super(CodenameHL17UICompat.HORIZONTAL);
		this.index = index;
	}

	public function addLabel(label:HLUILabel, width:Float):Void {
		label.componentWidth = width;
		label.componentHeight = 30;
		label.buildUI();
		labels.push(label);
		addComponent(label);
		componentWidth += width;
		componentHeight = Math.max(componentHeight, 30);
		setHitArea();
	}

	override public function layoutComponents():Void {
		super.layoutComponents();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		_hovered = visible && FlxG.mouse.overlaps(this);
		if (_hovered && FlxG.mouse.justPressed) {
			pressed = true;
			if (table != null) table.selectRow(this);
		}
		if (pressed && FlxG.mouse.justReleased) {
			pressed = false;
			if (_hovered && onRelease != null) onRelease();
		}
		for (label in labels) if (label != null)
			label.textCol = table != null && table.selectedRow == this
				? HLUILabel.TEXT_SELEC_COL : HLUILabel.TEXT_COL;
	}
}

@:keep
class HLUITable extends HLUIComponent {
	public var _rows:Array<HLUITableRow> = [];
	public var selectedRow:Null<HLUITableRow>;
	public var columnWidths:Array<Float> = [];

	public function new(sections:Array<Dynamic>, widths:Array<Int>) {
		super();
		if (widths != null) for (width in widths) columnWidths.push(width);
		var rowIndex = 0;
		if (sections != null) for (section in sections) {
			var columns:Array<Dynamic> = Reflect.field(section, 'columns');
			var rows:Array<Dynamic> = Reflect.field(section, 'rows');
			var header = new HLUITableRow(-1);
			if (columns != null) for (columnIndex in 0...columns.length) {
				var label = new HLUILabel(Std.string(columns[columnIndex]));
				label.textCol = HLUILabel.TEXT_SELEC_COL;
				header.addLabel(label, columnWidth(columnIndex));
			}
			addTableRow(header);
			if (rows != null) for (rowData in rows) {
				var row = new HLUITableRow(rowIndex++);
				if (rowData != null) for (columnIndex in 0...rowData.length) {
					var label = new HLUILabel(Std.string(rowData[columnIndex]));
					row.addLabel(label, columnWidth(columnIndex));
				}
				addTableRow(row);
			}
		}
	}

	function columnWidth(index:Int):Float
		return index >= 0 && index < columnWidths.length ? columnWidths[index] : 150;

	override public function layoutComponents():Void {
		var cursor:Float = 0;
		for (row in _rows) if (row != null) {
			row.flowOffset.set(0, cursor);
			row.syncPosition();
			cursor += row.componentHeight;
		}
	}

	function addTableRow(row:HLUITableRow):Void {
		row.table = this;
		row.componentHeight = Math.max(row.componentHeight, 30);
		row.componentWidth = Math.max(row.componentWidth, componentWidth);
		_rows.push(row);
		addComponent(row);
		componentHeight += row.componentHeight;
		componentWidth = Math.max(componentWidth, row.componentWidth);
		setHitArea();
	}

	public function selectRow(row:HLUITableRow):Void {
		if (row != null && _rows.indexOf(row) >= 0 && row.index >= 0) selectedRow = row;
	}

	override public function buildUI(?options:Dynamic):Void {
		super.buildUI(options);
		for (row in _rows) if (row != null) row.buildUI({background:row.index < 0});
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		for (row in _rows) if (row != null && row.index >= 0 && row.labels != null)
			for (label in row.labels)
				label.textCol = selectedRow == row ? HLUILabel.TEXT_SELEC_COL : HLUILabel.TEXT_COL;
	}

	override public function destroy():Void {
		for (row in _rows) if (row != null) row.table = null;
		_rows.resize(0);
		selectedRow = null;
		super.destroy();
	}
}
