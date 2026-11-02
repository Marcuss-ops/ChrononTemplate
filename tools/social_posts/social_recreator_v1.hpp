#pragma once
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

using J = nlohmann::json;
struct Recipe { const char* id; const char* platform; const char* author; const char* handle; const char* meta; const char* body; const char* metric; const char* kind; const char* theme; bool media; };
J makePlan(const Recipe& recipe);
const Recipe& recipe_yt01_video_watch_page();
const Recipe& recipe_yt02_comments_replies();
const Recipe& recipe_yt03_community_post();
const Recipe& recipe_yt04_shorts_player();
const Recipe& recipe_yt05_channel_profile();
const Recipe& recipe_ig01_feed_post();
const Recipe& recipe_ig02_carousel();
const Recipe& recipe_ig03_stories();
const Recipe& recipe_ig04_reels();
const Recipe& recipe_ig05_direct_messages();
const Recipe& recipe_tk01_for_you_video();
const Recipe& recipe_tk02_comments_replies();
const Recipe& recipe_tk03_creator_profile();
const Recipe& recipe_tk04_duet_stitch();
const Recipe& recipe_tk05_live_chat();
const Recipe& recipe_dc01_server_chat();
const Recipe& recipe_dc02_direct_messages();
const Recipe& recipe_dc03_announcement_embed();
const Recipe& recipe_dc04_forum_thread();
const Recipe& recipe_dc05_poll();
const Recipe& recipe_x01_single_post();
const Recipe& recipe_x02_media_post();
const Recipe& recipe_x03_thread();
const Recipe& recipe_x04_quote_reply();
const Recipe& recipe_x05_poll();
const std::vector<Recipe>& allSocialRecreatorV1Recipes();
