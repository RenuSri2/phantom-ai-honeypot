import { useState, useEffect } from 'react';
import { ref, onValue, off } from 'firebase/database';
import { db } from '../firebase';

export function useFirebaseListener(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!path) {
      setData(null);
      setLoading(false);
      return;
    }

    const dbRef = ref(db, path);
    setLoading(true);

    const listener = onValue(
      dbRef,
      (snapshot) => {
        setData(snapshot.exists() ? snapshot.val() : null);
        setLoading(false);
      },
      (err) => {
        console.error("Firebase subscription error:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => off(dbRef, 'value', listener);
  }, [path]);

  return { data, loading, error };
}
