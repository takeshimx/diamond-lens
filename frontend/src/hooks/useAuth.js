import { useState, useEffect } from 'react';
import {
    signInWithPopup,
    GoogleAuthProvider,
    signOut,
    onAuthStateChanged,
} from 'firebase/auth';
import { auth } from '../firebase';

const googleProvider = new GoogleAuthProvider();

export const useAuth = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Firebase の認証状態を監視
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
            setUser(firebaseUser);
            setLoading(false);
        });
        return () => unsubscribe();
    }, []);

    // Googleログイン
    const loginWithGoogle = async () => {
        setError('');
        try {
            await signInWithPopup(auth, googleProvider);
        } catch (err) {
            if (err.code === 'auth/popup-closed-by-user') {
                // ユーザーがポップアップを閉じた場合は何もしない
                return;
            }
            setError('Googleログインに失敗しました。もう一度お試しください。');
            throw err;
        }
    };

    // ログアウト
    const logout = async () => {
        await signOut(auth);
    };

    // IDトークンを取得（API呼び出し時に使用）
    const getIdToken = async () => {
        if (!auth.currentUser) return null;
        return await auth.currentUser.getIdToken();
    };

    return { user, loading, error, loginWithGoogle, logout, getIdToken };
};
