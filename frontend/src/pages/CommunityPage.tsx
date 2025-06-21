import React from 'react';
import { motion } from 'framer-motion';
import { Users, MessageSquare, Trophy, Star } from 'lucide-react';

const CommunityPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Community</h1>
          <p className="text-dark-400">Connect with fellow racers and share your achievements</p>
        </div>
        <button className="btn btn-primary btn-md flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          New Post
        </button>
      </div>

      {/* Community Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-5 h-5 text-primary-500" />
              <span className="text-sm text-dark-400">Members</span>
            </div>
            <div className="text-2xl font-bold text-white">--</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <MessageSquare className="w-5 h-5 text-success-500" />
              <span className="text-sm text-dark-400">Posts</span>
            </div>
            <div className="text-2xl font-bold text-white">--</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <Trophy className="w-5 h-5 text-warning-500" />
              <span className="text-sm text-dark-400">Achievements</span>
            </div>
            <div className="text-2xl font-bold text-white">--</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <Star className="w-5 h-5 text-secondary-500" />
              <span className="text-sm text-dark-400">Your Rank</span>
            </div>
            <div className="text-2xl font-bold text-white">--</div>
          </div>
        </motion.div>
      </div>

      {/* Community Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-white">Recent Posts</h3>
            </div>
            <div className="card-content">
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-4 bg-dark-900 rounded-lg border border-dark-600">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-sm font-bold">U</span>
                      </div>
                      <div>
                        <div className="font-medium text-white">Username</div>
                        <div className="text-xs text-dark-400">2 hours ago</div>
                      </div>
                    </div>
                    <p className="text-dark-300 text-sm mb-3">
                      Placeholder community post content. Connect to see real posts from the community.
                    </p>
                    <div className="flex items-center gap-4 text-xs text-dark-400">
                      <span className="flex items-center gap-1">
                        <Star className="w-3 h-3" />
                        0 likes
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        0 comments
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Leaderboard */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-white">Leaderboard</h3>
            </div>
            <div className="card-content">
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-dark-700 rounded-full flex items-center justify-center text-xs text-dark-400">
                      {i}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm text-white">Driver {i}</div>
                      <div className="text-xs text-dark-400">-- points</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Discord Integration */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-white">Discord</h3>
            </div>
            <div className="card-content">
              <p className="text-sm text-dark-300 mb-3">
                Join the TrackPro Discord community to chat with other racers.
              </p>
              <button className="btn btn-secondary btn-sm w-full">
                Connect Discord
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommunityPage;