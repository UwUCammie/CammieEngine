"""Metatables: __index, __newindex and __call through setmetatable/getmetatable."""
import unittest

from lua_translate_support import check_outputs, run_lua


CLASS_SETUP = """
local Animal = {}
Animal.__index = Animal
function Animal.new(name)
  local self = setmetatable({}, Animal)
  self.name = name
  return self
end
function Animal:speak() return self.name .. ' makes a sound' end
local Dog = setmetatable({}, {__index = Animal})
Dog.__index = Dog
function Dog.new(name)
  local self = Animal.new(name)
  return setmetatable(self, Dog)
end
function Dog:fetch() return self.name .. ' fetches' end
"""


class LuaMetatablesTest(unittest.TestCase):
    def test_metatables(self):
        check_outputs(self, [
            ("class_with_methods_through_index",
             CLASS_SETUP + "local d = Dog.new('rex')\nout(d:speak(), d:fetch(), getmetatable(d) == Dog, rawget(d, 'speak') == nil)",
             "rex makes a sound,rex fetches,true,true"),
            ("own_keys_win_over_index",
             "local defaults = {speed = 3, size = 2}\nlocal cfg = setmetatable({speed = 9}, {__index = defaults})\nout(cfg.speed, cfg.size, cfg['size'], cfg.none)",
             "9,2,2,nil"),
            ("index_function_gets_table_and_key",
             "local d = setmetatable({}, {__index = function(t, k) return k .. '!' end})\nout(d.hello, d[3])",
             "hello!,3!"),
            ("newindex_function_takes_new_keys_only",
             "local p = setmetatable({}, {__newindex = function(t, k, v) rawset(t, k, v * 2) end})\np.a = 5\np.a = 7\nout(p.a)",
             "7"),
            ("newindex_table_receives_the_write",
             "local store = {}\nlocal proxy = setmetatable({}, {__newindex = store, __index = store})\nproxy.a = 1\nproxy['b'] = 2\nout(rawget(proxy, 'a'), store.a, proxy.a, proxy.b)",
             "nil,1,1,2"),
            ("call_runs_with_the_table_first",
             "local counter = setmetatable({step = 2}, {__call = function(self, a) return a + self.step end})\nout(counter(4))",
             "6"),
            ("method_named_like_an_array_method",
             "local Q = {}\nQ.__index = Q\nfunction Q.new() return setmetatable({}, Q) end\nfunction Q:remove() return 'own remove' end\nfunction Q:push(v) return 'own push ' .. v end\nlocal q = Q.new()\nout(q:remove(), q:push(1))",
             "own remove,own push 1"),
            ("pairs_and_length_ignore_the_metatable",
             "local base = {x = 1, 10, 20}\nlocal t = setmetatable({y = 2}, {__index = base})\nlocal n = 0\nfor k, v in pairs(t) do n = n + 1 end\nout(n, #t)",
             "1,0"),
            ("protected_metatable",
             "local t = setmetatable({}, {__metatable = 'locked'})\nlocal ok = pcall(setmetatable, t, {})\nout(getmetatable(t), ok)",
             "locked,false"),
            ("removing_the_metatable",
             "local t = setmetatable({}, {__index = {a = 1}})\nsetmetatable(t, nil)\nout(t.a, getmetatable(t))",
             "nil,nil"),
            ("compound_assignment_reads_through_index",
             "local t = setmetatable({}, {__index = {score = 10}})\nt.score = t.score + 5\nout(t.score, getmetatable(t).__index.score)",
             "15,10"),
        ])

    def test_inline_metatables_are_no_longer_diagnosed(self):
        record = run_lua([("inline", "local d = setmetatable({}, {__index = {a = 1}})\nout(d.a)")])["inline"]
        self.assertNotIn("lua-metatable", record["diagnostics"])
        self.assertIn("luaSetMetatable(", record["hscript"])
        self.assertEqual(record["out"], "1")


if __name__ == "__main__":
    unittest.main()
