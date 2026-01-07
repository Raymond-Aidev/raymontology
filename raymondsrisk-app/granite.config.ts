import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'raymondsrisk', // 앱인토스 콘솔에서 설정한 앱 이름
  brand: {
    displayName: 'RaymondsRisk', // 화면에 노출될 앱의 한글 이름
    primaryColor: '#E74C3C', // RaymondsRisk 브랜드 컬러 (빨간색)
    icon: 'https://static.toss.im/appsintoss/4657/5a80478b-dc5e-4b02-974e-67b68bd7ed71.png', // 앱인토스 콘솔에서 업로드한 아이콘
  },
  web: {
    host: '192.168.35.235', // 실기기 테스트용 로컬 IP (ipconfig getifaddr en0로 확인)
    port: 5173,
    commands: {
      dev: 'vite --host', // --host 옵션으로 외부 접속 허용
      build: 'vite build', // 빌드 명령어
    },
  },
  webViewProps: {
    type: 'partner', // 'partner'(기본) 또는 'game'(전체화면)
  },
  permissions: [],
});
