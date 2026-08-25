from pathlib import Path
import shutil
import subprocess
from datetime import datetime

BOT = Path("bot.js")

if not BOT.exists():
    print("❌ bot.js not found. Make sure you are in ~/Silver-c5")
    raise SystemExit(1)

# ============================================================
# BACKUP
# ============================================================

backup = Path(
    f"bot.js.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
)

shutil.copy2(BOT, backup)

print(f"💾 Backup created: {backup}")

s = BOT.read_text()

# ============================================================
# 1. FIX BAN CONFIRMATION MESSAGE
# ============================================================

old = r'''          await sock.sendMessage(groupId, {
            text:
              "╭━━━〔 🚫 USER BANNED 〕━━━╮\\n\\n" +
              `👤 @${targetJid.split("@")[0]}\\n` +
              `🔒 Type: *${mode.toUpperCase()}*\\n` +
              "🚫 They cannot return to this group.\\n\\n" +
              "╰━━━━━━━━━━━━━━━━━━━━╯",
            mentions: [targetJid]
          });'''

new = r'''          const banText =
            mode === "bann"
              ? `╭━━━〔 🚫 USER BANNED 〕━━━╮

👤 @${targetJid.split("@")[0]}
🔒 Type: *BANN*
🚫 They were removed and cannot return to this group.

╰━━━━━━━━━━━━━━━━━━━━╯`
              : `╭━━━〔 🚫 USER REGISTERED 〕━━━╮

👤 @${targetJid.split("@")[0]}
🔒 Type: *BANN2*
📝 User registered on the group's ban list.
🚫 They will be blocked from returning.

╰━━━━━━━━━━━━━━━━━━━━╯`;

          await sock.sendMessage(groupId, {
            text: banText,
            mentions: [targetJid]
          });'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ Ban confirmation fixed")
else:
    print("⚠️ Ban confirmation block not found")

# ============================================================
# 2. MAKE BANN AND BANN2 DIFFERENT
# ============================================================

old = r'''          // Kick immediately
          try {

            await sock.groupParticipantsUpdate(
              groupId,
              [targetJid],
              "remove"
            );

          } catch (err) {

            logger.error(
              {
                target: targetJid,
                error: err.message
              },
              "Failed to kick banned user"
            );
          }'''

new = r'''          // .bann = remove immediately
          // .bann2 = register only; do not remove immediately
          if (mode === "bann") {
            try {
              await sock.groupParticipantsUpdate(
                groupId,
                [targetJid],
                "remove"
              );
            } catch (err) {
              logger.error(
                {
                  target: targetJid,
                  error: err.message
                },
                "Failed to kick banned user"
              );
            }
          }'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ .bann and .bann2 separated")
else:
    print("⚠️ Kick block not found")

# ============================================================
# 3. FIX LIST BANNED FORMATTING
# ============================================================

old = r'''          let text =
            "╭━━━〔 🚫 BANNED USERS 〕━━━╮\\n\\n";'''

new = '''          let text =
            `╭━━━〔 🚫 BANNED USERS 〕━━━╮

`;'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ List header fixed")

old = r'''              text +=
                `${index + 1}. @${jid.split("@")[0]}\\n` +
                `   🔒 ${info.mode || "bann"}\\n\\n`;'''

new = '''              text +=
                `${index + 1}. @${jid.split("@")[0]}
   🔒 ${(info.mode || "bann").toUpperCase()}

`;'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ List entries fixed")

# ============================================================
# 4. FIX LIST EMPTY MESSAGE
# ============================================================

old = r'''"╭━━━〔 🚫 BANNED USERS 〕━━━╮\\n\\n" +
                "📭 No banned users in this group.\\n\\n" +
                "╰━━━━━━━━━━━━━━━━━━━━━━━━╯"'''

new = '''`╭━━━〔 🚫 BANNED USERS 〕━━━╮

📭 No banned users in this group.

╰━━━━━━━━━━━━━━━━━━━━━━━━╯`'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ Empty ban list fixed")

# ============================================================
# 5. FIX BAN RESET MESSAGE
# ============================================================

old = r'''              "╭━━━〔 ♻️ BAN RESET 〕━━━╮\\n\\n" +
              `🗑️ Removed *${count}* banned user(s).\\n` +
              "✅ The group's ban list has been reset.\\n\\n" +
              "╰━━━━━━━━━━━━━━━━━━━━╯"'''

new = '''`╭━━━〔 ♻️ BAN RESET 〕━━━╮

🗑️ Removed *${count}* banned user(s).
✅ The group's ban list has been reset.

╰━━━━━━━━━━━━━━━━━━━━╯`'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ Ban reset message fixed")

# ============================================================
# 6. FIX UNBANN MESSAGE
# ============================================================

old = r'''              "╭━━━〔 ♻️ UNBANNED 〕━━━╮\\n\\n" +
              `👤 @${number}\\n` +
              "✅ User can now be added/join again.\\n\\n" +
              "╰━━━━━━━━━━━━━━━━━━━━╯"'''

new = '''`╭━━━〔 ♻️ UNBANNED 〕━━━╮

👤 @${number}
✅ User can now be added/join again.

╰━━━━━━━━━━━━━━━━━━━━╯`'''

if old in s:
    s = s.replace(old, new, 1)
    print("✅ Unbann message fixed")

# ============================================================
# 7. REMOVE DM BLOCKER FROM CURRENT GROUP SECTION
# ============================================================

dm_start = '''        // ==================================================
        // 🚫 DM BLOCKER
        // ==================================================

        if (command === "dmblocker") {'''

warn_start = '''        if (command === "warn") {'''

start = s.find(dm_start)

if start != -1:
    end = s.find(warn_start, start)

    if end != -1:
        s = s[:start] + s[end:]
        print("✅ Removed DM blocker from group command section")
    else:
        print("⚠️ Could not find DM blocker end")
else:
    print("ℹ️ DM blocker group section already absent")

# ============================================================
# 8. REMOVE DMB FROM GROUP SECTION
# ============================================================

dmb_start = '''        // ==================================================
        // ✏️ .DMB MSG
        // ==================================================

        if (
          command === "dmb" &&
          args[0]?.toLowerCase() === "msg"
        ) {'''

start = s.find(dmb_start)

if start != -1:
    end = s.find(warn_start, start)

    if end != -1:
        s = s[:start] + s[end:]
        print("✅ Removed .dmb from group command section")
    else:
        print("⚠️ Could not find .dmb end")
else:
    print("ℹ️ .dmb group section already absent")

# ============================================================
# 9. FIND DM COMMAND AREA
# ============================================================

# We insert before the existing DM ping command.
dm_anchor = '''        if (command === "ping"'''

if dm_anchor not in s:
    print("❌ Could not find DM command insertion point")
    print("↩️ Restoring backup")
    shutil.copy2(backup, BOT)
    raise SystemExit(1)

# ============================================================
# 10. INSERT DM BLOCKER
# ============================================================

dm_commands = '''        // ==================================================
        // 🚫 DM BLOCKER — DM ONLY
        // ==================================================

        if (command === "dmblocker" && canUseDM) {

          const option = args[0]?.toLowerCase();

          if (option === "on") {

            dmBlockerEnabled = true;
            saveData();

            await sock.sendMessage(message.key.remoteJid, {
              text: `╭━━━〔 🚫 DM BLOCKER 〕━━━╮

📡 Status: *ON* ✅
🛡️ Unauthorized DMs will be blocked.

╰━━━━━━━━━━━━━━━━━━━━╯`
            });

            return;
          }

          if (option === "off") {

            dmBlockerEnabled = false;
            saveData();

            await sock.sendMessage(message.key.remoteJid, {
              text: `╭━━━〔 🚫 DM BLOCKER 〕━━━╮

📡 Status: *OFF* ❌

╰━━━━━━━━━━━━━━━━━━━━╯`
            });

            return;
          }

          await sock.sendMessage(message.key.remoteJid, {
            text: `❌ Usage:

.dmblocker on
.dmblocker off`
          });

          return;
        }

        // ==================================================
        // ✏️ .DMB MSG — DM ONLY
        // ==================================================

        if (command === "dmb" && canUseDM) {

          if (args[0]?.toLowerCase() !== "msg") {

            await sock.sendMessage(message.key.remoteJid, {
              text: `❌ Usage:

.dmb msg your message

Current message:
${dmBlockerMessage}`
            });

            return;
          }

          const newMessage =
            args.slice(1).join(" ").trim();

          if (!newMessage) {

            await sock.sendMessage(message.key.remoteJid, {
              text: `❌ Usage:

.dmb msg your message

Current message:
${dmBlockerMessage}`
            });

            return;
          }

          dmBlockerMessage = newMessage;
          saveData();

          await sock.sendMessage(message.key.remoteJid, {
            text: `╭━━━〔 ✏️ DM BLOCK MESSAGE 〕━━━╮

✅ Message updated.

💬 ${dmBlockerMessage}

╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯`
          });

          return;
        }

'''

s = s.replace(dm_anchor, dm_commands + dm_anchor, 1)

print("✅ DM commands inserted into DM command section")

# ============================================================
# WRITE
# ============================================================

BOT.write_text(s)

print()
print("💾 bot.js saved")
print(f"💾 Backup: {backup}")

# ============================================================
# SYNTAX CHECK
# ============================================================

print()
print("🔎 Running node --check bot.js...")

result = subprocess.run(
    ["node", "--check", "bot.js"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✅ node --check bot.js PASSED")
else:
    print("❌ node --check bot.js FAILED")
    print(result.stderr)
    print()
    print("↩️ Restoring backup...")
    shutil.copy2(backup, BOT)
    print("✅ Original bot.js restored")
    raise SystemExit(1)

# ============================================================
# GIT CHECK
# ============================================================

print()
print("🔎 Running git diff --check...")

result = subprocess.run(
    ["git", "diff", "--check"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✅ git diff --check PASSED")
else:
    print("⚠️ git diff --check found whitespace issues:")
    print(result.stdout)
    print(result.stderr)

print()
print("================================================")
print("🎉 PATCH COMPLETE")
print("================================================")
print()
print("Next command:")
print("node --check bot.js")
print()
print("Then inspect:")
print("grep -n -E 'command === \"bann\"|command === \"bann2\"|command === \"dmblocker\"|command === \"dmb\"' bot.js")
