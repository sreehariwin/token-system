importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyDgPNgcGm3K7Xwd8ab6poo6qRJ1y8c6OOc",
    authDomain: "newproject-e631f.firebaseapp.com",
    projectId: "newproject-e631f",
    storageBucket: "newproject-e631f.firebasestorage.app",
    messagingSenderId: "844937946183",
    appId: "1:844937946183:web:f142e1799e511d4b2cbd62",
    measurementId: "G-HE01NPQZK6"
});

const messaging = firebase.messaging();


messaging.onBackgroundMessage(function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);
    
    // Customize notification here
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/firebase-logo.png' // Add your icon path
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});