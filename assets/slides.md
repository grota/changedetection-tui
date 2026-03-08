---
date: ' '
---

# Welcome to Changedetection-tui

This video shows a demo of the `changedetection-tui` program.

Explanation here on the **left**

actual program on the **right**.

---
# Disclaimer

You will sometimes see here the message:

*(You might want to pause here)*

As an hint to pause the video when needed.

---

# Installation

Let's install the program via uv:

```bash
uv tool install changedetection-tui
```

---
# Now

Let's launch it.

```bash
cdtui
```
---
# Now

And zoom for clarity

---
# *(You might want to pause here)*

It needs both the URL and the API-KEY.

No cli switch has been passed.

No env var is defined.

No config file exist.

So the program asks for them interactively.

Let's provide them (demo values).

---

# URL

```bash
http://localhost:5000
```

---

# API-KEY

```bash
a9fa87b8421663bd958d3a34a705e049
```

Let's provide (paste) the actual value for now.

More on that later.

---

# The main view

You can see filtering an grouping widgets at the top.

And a list of watches at the bottom.

Let's see them in action.

---

# Key Bindings can be seen at the bottom

They can be changed in settings.

---

# Jump mode

To quickly jump to focusable widgets.


---

# Now let's open the settings

Two sections.

Let's play around.

---
# Main sections

Here we see the 2 values:

- URL
- API-KEY

we provided earlier via interactive prompt.

Saving will persist this information to a config file.

---

# Let's quit and relaunch

No interactive prompt this time

Because the settings were persisted to a file.

---

# *(You might want to pause here)*

Let's cat that file

```bash
cat ~/.config/cdtui/config.yaml
```

⚠️ We do not want an hardcoded API key secret in a config file!

✅ We can specify the API-KEY via a `$SOME_VAR_WITH_API_KEY` syntax.

Let's do that.

---
# Safer storage of API-KEY

```bash
export CHANGEDETECTION_API_KEY=a9fa87b8421663bd958d3a34a705e049
```

---
# Safer storage of API-KEY

```bash
rm ~/.config/cdtui/config.yaml
```

---

# URL

```bash
http://localhost:5000
```
---
# API-KEY

We'll just paste in:

```bash
$CHANGEDETECTION_API_KEY
```
---
# That's reflected in the settings

And let's save the config.

And exit the program.
---

# *(You might want to pause here)*

Let's cat that file

```bash
cat ~/.config/cdtui/config.yaml
```

See that no secret is now stored on disk.

---

# That's all folks! 👋

Thank you for watching!
```

```
