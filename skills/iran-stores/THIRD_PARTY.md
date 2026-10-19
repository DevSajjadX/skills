# Third-party notices

The store modules in `stores/` are our own code. Their endpoints, query
strings and units were learned from the MIT-licensed MCP servers below and
re-implemented here with the standard library. Some request strings (Technolife's
GraphQL queries) are reused verbatim under the MIT license below. None of the
servers' test fixtures is copied, and we never run these servers: the only MCP
server we call is Pasavard's official hosted endpoint.

| Module | Learned from |
| --- | --- |
| `stores/digikala.py`, `stores/digikala_fresh.py` | digikala-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/technolife.py` | technolife-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/masterkala.py` | masterkala-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/khanoumi.py` | khanoumi-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/asalbanoo.py` | asalbanoo-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/taaghche.py` | taaghche-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/fidibo.py` | fidibo-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/sibook.py`, `blazor.py` | 30book-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/shopino.py` | shopino-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/torob.py` | torob-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/snappmarket.py` | snapp-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/okala.py` | okala-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/divar.py` | divar-mcp, Copyright (c) 2026 Sepehr Radmard |
| `stores/pasavard.py` | pasavard-mcp, Copyright (c) 2026 Ashkan Ayyoogh |

## MIT License

Copyright (c) 2026 Sepehr Radmard (digikala-mcp, torob-mcp, technolife-mcp, masterkala-mcp, khanoumi-mcp, asalbanoo-mcp, shopino-mcp, taaghche-mcp, fidibo-mcp, 30book-mcp, snapp-mcp, okala-mcp, divar-mcp)
Copyright (c) 2026 Ashkan Ayyoogh (pasavard-mcp)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
