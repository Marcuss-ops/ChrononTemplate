#include "social_recreator_v1.hpp"

const std::vector<Recipe>& allSocialRecreatorV1Recipes() {
    static const std::vector<Recipe> recipes = {
        recipe_yt01_video_watch_page(),
        recipe_yt02_comments_replies(),
        recipe_yt03_community_post(),
        recipe_yt04_shorts_player(),
        recipe_yt05_channel_profile(),
        recipe_ig01_feed_post(),
        recipe_ig02_carousel(),
        recipe_ig03_stories(),
        recipe_ig04_reels(),
        recipe_ig05_direct_messages(),
        recipe_tk01_for_you_video(),
        recipe_tk02_comments_replies(),
        recipe_tk03_creator_profile(),
        recipe_tk04_duet_stitch(),
        recipe_tk05_live_chat(),
        recipe_dc01_server_chat(),
        recipe_dc02_direct_messages(),
        recipe_dc03_announcement_embed(),
        recipe_dc04_forum_thread(),
        recipe_dc05_poll(),
        recipe_x01_single_post(),
        recipe_x02_media_post(),
        recipe_x03_thread(),
        recipe_x04_quote_reply(),
        recipe_x05_poll()
    };
    return recipes;
}
