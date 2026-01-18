"use client";

/* Core CSS required for Ionic components to work properly */
import '@ionic/react/css/core.css';
import '@ionic/react/css/normalize.css';
import '@ionic/react/css/structure.css';
import '@ionic/react/css/typography.css';

/* Optional CSS utils that can be commented out */
import '@ionic/react/css/padding.css';
// import '@ionic/react/css/float-elements.css';
// import '@ionic/react/css/text-alignment.css';
// import '@ionic/react/css/text-transformation.css';
// import '@ionic/react/css/flex-utils.css';
// import '@ionic/react/css/display.css';

import {
  IonContent,
  IonHeader,
  IonPage,
  IonTitle,
  IonToolbar,
  IonButton,
  IonIcon,
  IonCard,
  IonCardHeader,
  IonCardTitle,
  IonCardContent,
  setupIonicReact
} from '@ionic/react';
import { sendOutline, logoNoSmoking } from 'ionicons/icons';
import { useEffect, useState } from 'react';

// Initialize Ionic
setupIonicReact();

export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null; // Hydration fix

  // 텔레그램 봇 이름 설정
  const BOT_USERNAME = "Stock_Now_Bot";
  const TELEGRAM_LINK = `https://t.me/${BOT_USERNAME}?start=web_user`;

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>Stock Now 🚀</IonTitle>
        </IonToolbar>
      </IonHeader>
      <IonContent className="ion-padding" style={{ '--background': '#f0f2f5' }}>
        <div className="flex flex-col items-center justify-center h-full space-y-8">

          {/* Hero Section */}
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-bold text-gray-800">
              실시간 AI 투자 비서
            </h1>
            <p className="text-lg text-gray-600">
              텔레그램 하나로 끝내는<br />
              나만의 주식 분석 리포트
            </p>
          </div>

          {/* Action Card */}
          <IonCard className="w-full max-w-sm">
            {/* <IonCardHeader>
              <IonCardTitle className="text-center">지금 바로 시작하기</IonCardTitle>
            </IonCardHeader> */}
            <IonCardContent className="flex flex-col items-center space-y-4 pt-4">

              {/* Fake QR Code Area */}
              {/* <div className="w-48 h-48 bg-gray-200 flex items-center justify-center rounded-lg border-2 border-dashed border-gray-400">
                <span className="text-gray-500">QR Code Here</span>
              </div> */}

              <IonButton expand="block" color="primary" href={TELEGRAM_LINK} target="_blank">
                <IonIcon icon={sendOutline} slot="start" />
                텔레그램 봇 연결하기
              </IonButton>

              <p className="text-xs text-gray-400 text-center">
                * 위 버튼을 누르면 텔레그램으로 이동하여<br />
                자동으로 구독이 시작됩니다.
              </p>
            </IonCardContent>
          </IonCard>

        </div>
      </IonContent>
    </IonPage>
  );
}
