import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(req: NextRequest) {
    // '/admin' 경로에 대해서만 검사
    if (req.nextUrl.pathname.startsWith('/admin')) {
        const basicAuth = req.headers.get('authorization');

        if (basicAuth) {
            const authValue = basicAuth.split(' ')[1];
            // atob: Base64 디코딩
            const [user, pwd] = atob(authValue).split(':');

            // 🔐 아이디/비번 설정 (추후 환경변수로 변경 권장)
            // USER: admin
            // PASS: hunter
            if (user === 'admin' && pwd === 'hunter') {
                return NextResponse.next();
            }
        }

        // 인증 실패 시 로그인 팝업 띄움
        return new NextResponse('Reason Hunter Admin: Access Denied', {
            status: 401,
            headers: {
                'WWW-Authenticate': 'Basic realm="Admin Access"',
            },
        });
    }

    return NextResponse.next();
}

// 미들웨어 적용 범위
export const config = {
    matcher: '/admin/:path*',
};
