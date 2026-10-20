-- Convert blog 8 of the old wp2.do.cnshost.net multisite into a standalone
-- site with the wp_ prefix, and strip what the 2026 compromise left behind.
--
-- Expects the database to contain the raw wp_8_* tables plus the network-wide
-- wp_users / wp_usermeta / wp_site / wp_sitemeta / wp_blogs tables.

-- Network tables are not needed by a single site.
DROP TABLE IF EXISTS wp_site, wp_sitemeta, wp_blogs;

-- Users: keep only members of blog 8, drop multisite-only columns.
DELETE FROM wp_users
 WHERE ID NOT IN (SELECT user_id FROM wp_usermeta WHERE meta_key = 'wp_8_capabilities');
DELETE FROM wp_usermeta WHERE user_id NOT IN (SELECT ID FROM wp_users);
ALTER TABLE wp_users DROP COLUMN IF EXISTS spam, DROP COLUMN IF EXISTS deleted;

-- Usermeta: drop other blogs' keys (including blog 1's unprefixed wp_ keys),
-- then move blog 8's keys to the wp_ prefix. Drop sessions so every login
-- issued by the compromised server is invalid.
DELETE FROM wp_usermeta
 WHERE meta_key REGEXP '^wp_[0-9]+_' AND meta_key NOT LIKE 'wp\_8\_%';
DELETE FROM wp_usermeta
 WHERE meta_key IN ('wp_capabilities', 'wp_user_level', 'wp_user-settings',
                    'wp_user-settings-time', 'wp_dashboard_quick_press_last_post_id',
                    'wp_persisted_preferences',
                    'primary_blog', 'source_domain', 'session_tokens');
UPDATE wp_usermeta SET meta_key = CONCAT('wp_', SUBSTRING(meta_key, 6))
 WHERE meta_key LIKE 'wp\_8\_%';

-- Rename every wp_8_ table to wp_.
SET @renames = (
  SELECT GROUP_CONCAT(CONCAT('`', table_name, '` TO `wp_', SUBSTRING(table_name, 6), '`'))
    FROM information_schema.tables
   WHERE table_schema = DATABASE() AND table_name LIKE 'wp\_8\_%');
SET @sql = CONCAT('RENAME TABLE ', @renames);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

UPDATE wp_options SET option_name = 'wp_user_roles' WHERE option_name = 'wp_8_user_roles';

-- Leftovers from the malware plugins and removed plugins.
DELETE FROM wp_options WHERE option_name LIKE '%Nxploited%';
DELETE FROM wp_options WHERE option_name LIKE 'ai1wm%' OR option_name LIKE 'ai1wmme%';
DELETE FROM wp_options WHERE option_name LIKE '\_wpforms\_transient%htaccess%';

-- Caches and logs: transients (incl. ~10k geolocation entries), cron
-- (rebuilt by WordPress and plugins on next load), 404 / redirect logs,
-- shopper sessions.
DELETE FROM wp_options WHERE option_name LIKE '\_transient\_%' OR option_name LIKE '\_site\_transient\_%';
DELETE FROM wp_options WHERE option_name IN ('cron', 'recently_edited', 'rewrite_rules');
TRUNCATE wp_redirection_404;
TRUNCATE wp_redirection_logs;
TRUNCATE wp_woocommerce_sessions;
DELETE FROM wp_actionscheduler_logs;
DELETE FROM wp_actionscheduler_actions WHERE status IN ('complete', 'failed', 'canceled');

-- active_plugins is reset by import-from-multisite.sh with wp-cli.
UPDATE wp_options SET option_value = 'a:0:{}' WHERE option_name IN ('recently_activated', 'uninstall_plugins');
