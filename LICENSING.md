# Licensing

**License: [GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later).**

Two things this license guarantees, and they are exactly the two things this
project wants:

1. **Attribution.** Anyone who uses, modifies, or redistributes the code must
   keep the copyright notices and the license text.
2. **Derivative works stay open.** Anyone who builds on the code must release
   their version under the same license — including when they only run it as a
   network service.

## Why AGPL-3.0 and not Apache-2.0

The repository used to carry a custom source-available license (OIE-PCS-1.0)
plus an Apache-2.0 fallback. The custom text protected the project's interests
but almost nobody recognizes it, which defeats the purpose of a license. So the
custom text is gone and the requirement is expressed with a standard license.

| License | Attribution required | Modifications must be open | Hosted service must publish source | Recognized |
| --- | --- | --- | --- | --- |
| Apache-2.0 | yes | **no** | no | yes |
| MPL-2.0 | yes | only modified files | no | yes |
| GPL-3.0 | yes | yes | **no** (only on distribution) | yes |
| **AGPL-3.0** | **yes** | **yes** | **yes** | **yes** |
| OIE-PCS-1.0 (old) | yes | partly | partly | no |

Apache-2.0 was the previous `LICENSE`, but it is *permissive*: a company can take
the code, change it, ship it closed-source, and only needs to keep the notice.
That contradicts the requirement "programs built on this source must be open".
AGPL-3.0 is the standard license that covers all three columns, and its §13
network clause matters here: an audit tool is exactly the kind of thing a relay
platform could wrap into a hosted service without ever distributing a binary.

If AGPL is too strong for a specific integration, the practical alternatives are
**GPL-3.0** (drops only the network clause) or **MPL-2.0** (file-level
copyleft). This repository deliberately uses AGPL-3.0-or-later.

## What you must do

- Keep `LICENSE`, the copyright headers, and [NOTICE](NOTICE) intact.
- If you distribute a modified version, publish the complete corresponding
  source under AGPL-3.0-or-later.
- If you let others use a modified version over a network, offer them that same
  source (AGPL §13).
- State changes you made and the date, as required by AGPL §5.

## What you may do

- Run the tool for yourself or inside your organization for any purpose.
- Audit endpoints you are authorized to use.
- Reuse `data/probes/*.jsonl` under AGPL-3.0-or-later or CC BY-SA 4.0 (see
  [CORE-COMPONENTS.md](CORE-COMPONENTS.md)).
- Charge money for services built on it, as long as the source obligations are
  met.

Model outputs produced by running the tool are yours; the project claims no
rights over them.

## Commercial exception (dual licensing)

The copyright holder owns the code and can also license it under different
terms. If AGPL-3.0-or-later does not fit your product (for example, a
closed-source appliance), open an issue titled `commercial licensing` in this
repository to discuss a separate commercial license.

This is the standard dual-licensing model: the community gets AGPL-3.0-or-later,
and the copyright holder may grant exceptions. No exception is granted by
default.

## FAQ

**Does using the CLI to audit an endpoint make my product a derivative?**
No. Running the tool does not create a derivative work. The obligations start
when you modify and redistribute the program, or offer a modified version as a
network service.

**Can I publish my own probe bank?**
Yes. A separate question bank is your work. If you copy or adapt questions from
`data/probes/`, keep attribution and share under AGPL-3.0-or-later or CC BY-SA 4.0.

**Can I use the JSON reports in a commercial dashboard?**
Yes. The reports are data output, not the program.

**Is there a warranty?**
No. The software is provided "as is", without warranty of any kind, as stated in
AGPL §15-§17. A capability verdict is evidence, not a guarantee about a
provider.
