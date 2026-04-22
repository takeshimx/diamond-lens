import { Activity } from 'lucide-react';

const LoginScreen = ({ authError, isCheckingAuth, handleGoogleLogin }) => (
  <div className="fixed inset-0 flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-black transition-colors duration-200">
    <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg w-full max-w-md transition-colors duration-200">
      <div className="text-center mb-6">
        <div className="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
          <Activity className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Diamond Lens</h1>
        <p className="text-gray-600 dark:text-gray-300">MLB Stats Assistant</p>
      </div>

      <div className="space-y-4">
        {authError && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">{authError}</p>
          </div>
        )}

        <button
          onClick={handleGoogleLogin}
          disabled={isCheckingAuth}
          className="w-full px-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-3 transition-colors duration-200"
        >
          {isCheckingAuth ? (
            <>
              <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
              ログイン中...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Google でログイン
            </>
          )}
        </button>
      </div>
    </div>
  </div>
);

export default LoginScreen;
