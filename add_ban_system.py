from pathlib import Path
import shutil
import sys

FILE = Path("bot.js")
BACKUP = Path("bot.js.pre-ban-system-backup")

if not FILE.exists():
    print("❌ bot.js not found.")
    sys.exit(1)

src = FILE.read_text()

if "const bannedUsers = {};" in src:
    print("⚠️ Ban system already appears to be installed.")
    print("❌ NO changes made.")
    sys.exit(0)

# ============================================================
# SAFE BACKUP
# ============================================================

shutil.copy2(FILE, BACKUP)
print(f"✅ Backup created: {BACKUP}")


def replace_once(old, new, label):
    global src

    count = src.count(old)

    if count != 1:
        print(f"❌ {label}: expected 1 match, found {count}")
        print("❌ RESTORING BACKUP — NO changes made.")
        shutil.copy2(BACKUP, FILE)
        sys.exit(1)

    src = src.replace(old, new, 1)
    print(f"✅ {label}")


# ============================================================
# 1. STORAGE VARIABLES
# ============================================================

replace_once(
'''const userWarns = {};
''',
'''const userWarns = {};

// ============================================
// 🚫 BAN SYSTEM
// ============================================

// { groupJid: { userJid: { mode, bannedAt, bannedBy } } }
const bannedUsers = {};

// ============================================
// 🚫 DM BLOCKER
// ============================================

let dmBlockerEnabled = false;
let dmBlockerMessage = "❌ You cannot message this bot.";

''',
"Ban/DM storage variables"
)


# ============================================================
# 2. LOAD FROM JSON
# ============================================================

replace_once(
'''      if (data.userWarns) {
        Object.assign(userWarns, data.userWarns);
      }

      // Load sudo users
''',
'''      if (data.userWarns) {
        Object.assign(userWarns, data.userWarns);
      }

      // Load banned users
      if (data.bannedUsers) {
        Object.assign(bannedUsers, data.bannedUsers);
      }

      // Load DM blocker settings
      if (data.dmBlockerEnabled !== undefined) {
        dmBlockerEnabled = Boolean(data.dmBlockerEnabled);
      }

      if (typeof data.dmBlockerMessage === "string") {
        dmBlockerMessage = data.dmBlockerMessage;
      }

      // Load sudo users
''',
"JSON loading"
)


# ============================================================
# 3. SAVE TO JSON
# ============================================================

replace_once(
'''      userWarns,
      sudoUsers,
''',
'''      userWarns,

      bannedUsers,
      dmBlockerEnabled,
      dmBlockerMessage,

      sudoUsers,
''',
"JSON saving"
)


# ============================================================
# 4. SUPABASE — SAVE GROUP BANS
# ============================================================

replace_once(
'''      antiBot: antiBotGroups[groupJid] ?? false,
      antiBotSignatures: [...antiBotSignatures],

      nightMode: nightModeGroups.includes(groupJid),
''',
'''      antiBot: antiBotGroups[groupJid] ?? false,
      antiBotSignatures: [...antiBotSignatures],

      // Ban system
      bannedUsers: bannedUsers[groupJid] ?? {},

      nightMode: nightModeGroups.includes(groupJid),
''',
"Supabase ban backup"
)


# ============================================================
# 5. SUPABASE — LOAD GROUP BANS
# ============================================================

replace_once(
'''      antiBotGroups[groupId] =
        Boolean(settings.antiBot);

      activityTracking[groupId] =
''',
'''      antiBotGroups[groupId] =
        Boolean(settings.antiBot);

      // Restore banned users for this group
      if (
        settings.bannedUsers &&
        typeof settings.bannedUsers === "object"
      ) {
        bannedUsers[groupId] =
          settings.bannedUsers;
      }

      activityTracking[groupId] =
''',
"Supabase ban loading"
)


# ============================================================
# 6. AUTOMATIC BAN CHECK WHEN SOMEONE JOINS
# ============================================================

replace_once(
'''    if (action === 'add') {
      // Check if welcome is enabled for this group (disabled by default)
      if (!welcomeEnabled[groupJid]) {
        return;
      }

      for (const participant of participants) {
''',
'''    if (action === 'add') {

      // ============================================
      // 🚫 AUTOMATIC BANNED USER PROTECTION
      // ============================================

      const groupBans =
        bannedUsers[groupJid] || {};

      for (const participant of participants) {

        const participantJid =
          typeof participant === "string"
            ? participant
            : participant?.id ||
              participant?.jid ||
              String(participant);

        if (groupBans[participantJid]) {

          const banInfo =
            groupBans[participantJid];

          try {

            await sock.sendMessage(groupJid, {
              text:
                "╭━━━〔 🚫 BANNED USER 〕━━━╮\\n\\n" +
                `👤 @${participantJid.split("@")[0]}\\n` +
                "❌ This user is banned from this group.\\n" +
                "👢 Removing automatically...\\n\\n" +
                "╰━━━━━━━━━━━━━━━━━━━━╯",
              mentions: [participantJid]
            });

            await sock.groupParticipantsUpdate(
              groupJid,
              [participantJid],
              "remove"
            );

            logger.info(
              {
                groupId: groupJid,
                user: participantJid,
                mode: banInfo.mode
              },
              "Banned user automatically removed"
            );

          } catch (err) {

            logger.error(
              {
                groupId: groupJid,
                user: participantJid,
                error: err.message
              },
              "Failed to remove banned user"
            );
          }
        }
      }

      // Continue with normal welcome handling
      if (!welcomeEnabled[groupJid]) {
        return;
      }

      for (const participant of participants) {
''',
"Automatic banned-user detection"
)


# ============================================================
# 7. BAN COMMANDS
# Insert immediately before normal .warn
# ============================================================

replace_once(
'''        if (command === "warn") {
''',
r'''        // ==================================================
        // 🚫 .BANN / .BANN2
        // ==================================================

        if (
          command === "bann" ||
          command === "bann2"
        ) {

          const groupId =
            message.key.remoteJid;

          if (!isGroup) {
            await sock.sendMessage(groupId, {
              text:
                "❌ This command only works in groups."
            });
            return;
          }

          let targetJid = null;

          const mentions =
            message.message
              .extendedTextMessage
              ?.contextInfo
              ?.mentionedJid;

          if (
            mentions &&
            mentions.length > 0
          ) {

            targetJid = mentions[0];

          } else {

            const context =
              message.message
                .extendedTextMessage
                ?.contextInfo;

            if (context?.participant) {
              targetJid =
                context.participant;
            }
          }

          if (!targetJid) {
            await sock.sendMessage(groupId, {
              text:
                "❌ Reply to or mention the user you want to ban."
            });
            return;
          }

          if (!bannedUsers[groupId]) {
            bannedUsers[groupId] = {};
          }

          const mode =
            command === "bann"
              ? "bann"
              : "bann2";

          bannedUsers[groupId][targetJid] = {
            mode,
            bannedAt:
              new Date().toISOString(),
            bannedBy:
              message.key.participant ||
              message.key.remoteJid
          };

          // Save locally + Supabase
          saveData();
          await saveGroupSettingsToSupabase(groupId);

          // Kick immediately
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

          await sock.sendMessage(groupId, {
            text:
              "╭━━━〔 🚫 USER BANNED 〕━━━╮\\n\\n" +
              `👤 @${targetJid.split("@")[0]}\\n` +
              `🔒 Type: *${mode.toUpperCase()}*\\n` +
              "🚫 They cannot return to this group.\\n\\n" +
              "╰━━━━━━━━━━━━━━━━━━━━╯",
            mentions: [targetJid]
          });

          return;
        }


        // ==================================================
        // ♻️ .UNBANN
        // .unbann 234xxxxxxxxxx
        // ==================================================

        if (command === "unbann") {

          const groupId =
            message.key.remoteJid;

          if (!isGroup) {
            await sock.sendMessage(groupId, {
              text:
                "❌ This command only works in groups."
            });
            return;
          }

          const number =
            args
              .join("")
              .replace(/[^\d]/g, "");

          if (!number) {
            await sock.sendMessage(groupId, {
              text:
                "❌ Usage:\\n" +
                ".unbann 234xxxxxxxxxx"
            });
            return;
          }

          const groupBans =
            bannedUsers[groupId] || {};

          const targetJid =
            Object.keys(groupBans).find(
              jid =>
                jid.split("@")[0] === number
            );

          if (!targetJid) {
            await sock.sendMessage(groupId, {
              text:
                `ℹ️ ${number} is not banned in this group.`
            });
            return;
          }

          delete groupBans[targetJid];

          if (
            Object.keys(groupBans).length === 0
          ) {
            delete bannedUsers[groupId];
          }

          saveData();
          await saveGroupSettingsToSupabase(groupId);

          await sock.sendMessage(groupId, {
            text:
              "╭━━━〔 ♻️ UNBANNED 〕━━━╮\\n\\n" +
              `👤 @${number}\\n` +
              "✅ User can now be added/join again.\\n\\n" +
              "╰━━━━━━━━━━━━━━━━━━━━╯"
          });

          return;
        }


        // ==================================================
        // 📋 .LIST BANNED
        // ==================================================

        if (
          command === "list" &&
          args[0]?.toLowerCase() === "banned"
        ) {

          const groupId =
            message.key.remoteJid;

          if (!isGroup) {
            await sock.sendMessage(groupId, {
              text:
                "❌ This command only works in groups."
            });
            return;
          }

          const groupBans =
            bannedUsers[groupId] || {};

          const entries =
            Object.entries(groupBans);

          if (entries.length === 0) {

            await sock.sendMessage(groupId, {
              text:
                "╭━━━〔 🚫 BANNED USERS 〕━━━╮\\n\\n" +
                "📭 No banned users in this group.\\n\\n" +
                "╰━━━━━━━━━━━━━━━━━━━━━━━━╯"
            });

            return;
          }

          let text =
            "╭━━━〔 🚫 BANNED USERS 〕━━━╮\\n\\n";

          entries.forEach(
            ([jid, info], index) => {

              text +=
                `${index + 1}. @${jid.split("@")[0]}\\n` +
                `   🔒 ${info.mode || "bann"}\\n\\n`;
            }
          );

          text +=
            "╰━━━━━━━━━━━━━━━━━━━━━━━━╯";

          await sock.sendMessage(groupId, {
            text,
            mentions:
              entries.map(
                ([jid]) => jid
              )
          });

          return;
        }


        // ==================================================
        // ♻️ .RESET BANNED
        // ==================================================

        if (
          command === "reset" &&
          args[0]?.toLowerCase() === "banned"
        ) {

          const groupId =
            message.key.remoteJid;

          if (!isGroup) {
            await sock.sendMessage(groupId, {
              text:
                "❌ This command only works in groups."
            });
            return;
          }

          const count =
            Object.keys(
              bannedUsers[groupId] || {}
            ).length;

          delete bannedUsers[groupId];

          saveData();
          await saveGroupSettingsToSupabase(groupId);

          await sock.sendMessage(groupId, {
            text:
              "╭━━━〔 ♻️ BAN RESET 〕━━━╮\\n\\n" +
              `🗑️ Removed *${count}* banned user(s).\\n` +
              "✅ The group's ban list has been reset.\\n\\n" +
              "╰━━━━━━━━━━━━━━━━━━━━╯"
          });

          return;
        }


        // ==================================================
        // 🚫 DM BLOCKER
        // ==================================================

        if (command === "dmblocker") {

          if (!isDM) {
            await sock.sendMessage(
              message.key.remoteJid,
              {
                text:
                  "❌ Use this command in DM."
              }
            );
            return;
          }

          if (!canUseDM) {
            return;
          }

          const option =
            args[0]?.toLowerCase();

          if (option === "on") {

            dmBlockerEnabled = true;
            saveData();

            await sock.sendMessage(
              message.key.remoteJid,
              {
                text:
                  "╭━━━〔 🚫 DM BLOCKER 〕━━━╮\\n\\n" +
                  "📡 Status: *ON* ✅\\n" +
                  "🛡️ Unauthorized DMs will be blocked.\\n\\n" +
                  "╰━━━━━━━━━━━━━━━━━━━━╯"
              }
            );

            return;
          }

          if (option === "off") {

            dmBlockerEnabled = false;
            saveData();

            await sock.sendMessage(
              message.key.remoteJid,
              {
                text:
                  "╭━━━〔 🚫 DM BLOCKER 〕━━━╮\\n\\n" +
                  "📡 Status: *OFF* ❌\\n\\n" +
                  "╰━━━━━━━━━━━━━━━━━━━━╯"
              }
            );

            return;
          }

          await sock.sendMessage(
            message.key.remoteJid,
            {
              text:
                "❌ Usage:\\n" +
                ".dmblocker on\\n" +
                ".dmblocker off"
            }
          );

          return;
        }


        // ==================================================
        // ✏️ .DMB MSG
        // ==================================================

        if (
          command === "dmb" &&
          args[0]?.toLowerCase() === "msg"
        ) {

          if (!canUseDM) {
            return;
          }

          const newMessage =
            args
              .slice(1)
              .join(" ")
              .trim();

          if (!newMessage) {

            await sock.sendMessage(
              message.key.remoteJid,
              {
                text:
                  "❌ Usage:\\n" +
                  ".dmb msg your message\\n\\n" +
                  `Current message:\\n${dmBlockerMessage}`
              }
            );

            return;
          }

          dmBlockerMessage =
            newMessage;

          saveData();

          await sock.sendMessage(
            message.key.remoteJid,
            {
              text:
                "╭━━━〔 ✏️ DM BLOCK MESSAGE 〕━━━╮\\n\\n" +
                "✅ Message updated.\\n\\n" +
                `💬 ${dmBlockerMessage}\\n\\n` +
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
            }
          );

          return;
        }


        if (command === "warn") {
''',
"Ban/DM commands"
)


# ============================================================
# 8. DM BLOCKER ENFORCEMENT
# ============================================================

replace_once(
'''      const isGroup = message.key.remoteJid.endsWith("@g.us");
      const isDM = !isGroup;

      // ============================================
      // EXP SYSTEM — AUTOMATIC MESSAGE XP
''',
'''      const isGroup = message.key.remoteJid.endsWith("@g.us");
      const isDM = !isGroup;

      // ============================================
      // 🚫 DM BLOCKER ENFORCEMENT
      // ============================================

      if (
        isDM &&
        dmBlockerEnabled &&
        !message.key.fromMe
      ) {

        const senderJid =
          message.key.participant ||
          message.key.remoteJid;

        const senderNumber =
          senderJid?.split("@")[0];

        const ownerNumber =
          BOT_OWNER?.split("@")[0];

        const isOwner =
          Boolean(
            senderNumber &&
            ownerNumber &&
            senderNumber === ownerNumber
          );

        const isSudo =
          Array.isArray(sudoUsers) &&
          sudoUsers.some(
            user =>
              String(user).split("@")[0] ===
              senderNumber
          );

        if (!isOwner && !isSudo) {

          try {

            await sock.sendMessage(
              message.key.remoteJid,
              {
                text: dmBlockerMessage
              }
            );

            await sock.updateBlockStatus(
              message.key.remoteJid,
              "block"
            );

            logger.info(
              {
                user:
                  message.key.remoteJid
              },
              "Unauthorized DM blocked"
            );

          } catch (err) {

            logger.error(
              {
                user:
                  message.key.remoteJid,
                error:
                  err.message
              },
              "Failed to block unauthorized DM"
            );
          }

          return;
        }
      }

      // ============================================
      // EXP SYSTEM — AUTOMATIC MESSAGE XP
''',
"DM blocker enforcement"
)


# ============================================================
# WRITE FILE
# ============================================================

FILE.write_text(src)

print()
print("🎉 BAN + DM BLOCKER PATCH COMPLETE!")
print()
print("Added:")
print("  ✅ .bann")
print("  ✅ .bann2")
print("  ✅ .unbann")
print("  ✅ .list banned")
print("  ✅ .reset banned")
print("  ✅ Automatic banned-user detection")
print("  ✅ Automatic kick + mention")
print("  ✅ .dmblocker on")
print("  ✅ .dmblocker off")
print("  ✅ .dmb msg")
print("  ✅ JSON persistence")
print("  ✅ Supabase ban persistence")
print()
print(f"💾 Backup: {BACKUP}")
