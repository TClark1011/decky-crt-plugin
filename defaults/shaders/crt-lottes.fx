// CRT-Lottes for gamescope's ReShade runtime.
//
// Adapted from Timothy Lottes' public domain "CRT styled scan-line shader"
// (the libretro crt-lottes shader). Changes from the original:
// - Self-contained: no ReShade.fxh, no extra textures, no runtime uniforms,
//   because gamescope only supports a subset of ReShade and cannot change
//   uniforms at runtime.
// - The emulated CRT resolution is derived from the buffer size, since the
//   filter covers whole-screen content (Steam UI and games) rather than a
//   fixed low-resolution emulator frame.
// - Each scanline samples two source rows so thin UI detail survives.
//
// Every tunable is a preprocessor define, so a wrapper file can override it
// with #define before #include-ing this file.

#ifndef CRT_LINE_PITCH
#define CRT_LINE_PITCH 3.0 // Buffer pixels per emulated scanline
#endif
#ifndef CRT_PIXEL_PITCH
#define CRT_PIXEL_PITCH 1.0 // Buffer pixels per emulated horizontal pixel
#endif
#ifndef CRT_HARD_SCAN
#define CRT_HARD_SCAN -8.0 // Scanline sharpness: -8 soft, -16 hard
#endif
#ifndef CRT_HARD_PIX
#define CRT_HARD_PIX -3.0 // Horizontal sharpness: -2 soft, -4 hard
#endif
#ifndef CRT_WARP_X
#define CRT_WARP_X 0.015 // Horizontal screen curvature
#endif
#ifndef CRT_WARP_Y
#define CRT_WARP_Y 0.02 // Vertical screen curvature
#endif
#ifndef CRT_MASK_DARK
#define CRT_MASK_DARK 0.5
#endif
#ifndef CRT_MASK_LIGHT
#define CRT_MASK_LIGHT 1.5
#endif
#ifndef CRT_SHADOW_MASK
#define CRT_SHADOW_MASK 3 // 0 none, 1 TV, 2 aperture grille, 3 stretched VGA, 4 VGA
#endif
#ifndef CRT_BRIGHT_BOOST
#define CRT_BRIGHT_BOOST 1.0
#endif
#ifndef CRT_BLOOM
#define CRT_BLOOM 1
#endif
#ifndef CRT_BLOOM_AMOUNT
#define CRT_BLOOM_AMOUNT 0.15
#endif
#ifndef CRT_HARD_BLOOM_PIX
#define CRT_HARD_BLOOM_PIX -1.5
#endif
#ifndef CRT_HARD_BLOOM_SCAN
#define CRT_HARD_BLOOM_SCAN -2.0
#endif
#ifndef CRT_SHAPE
#define CRT_SHAPE 2.0 // Filter kernel shape: 2 gaussian, higher is sharper
#endif
#ifndef CRT_LINEAR_GAMMA
#define CRT_LINEAR_GAMMA 1
#endif

static const float2 CrtRes = float2(BUFFER_WIDTH / CRT_PIXEL_PITCH, BUFFER_HEIGHT / CRT_LINE_PITCH);
static const float2 CrtWarp = float2(CRT_WARP_X, CRT_WARP_Y);

texture CrtBackBufferTex : COLOR;
sampler CrtBackBuffer
{
	Texture = CrtBackBufferTex;
	MinFilter = LINEAR;
	MagFilter = LINEAR;
	AddressU = CLAMP;
	AddressV = CLAMP;
};

void CrtFullscreenVS(in uint id : SV_VertexID, out float4 position : SV_Position, out float2 texcoord : TEXCOORD)
{
	texcoord.x = (id == 2) ? 2.0 : 0.0;
	texcoord.y = (id == 1) ? 2.0 : 0.0;
	position = float4(texcoord * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
}

float ToLinear1(float c)
{
	return (c <= 0.04045) ? c / 12.92 : pow(abs((c + 0.055) / 1.055), 2.4);
}

float3 ToLinear(float3 c)
{
#if CRT_LINEAR_GAMMA
	return float3(ToLinear1(c.r), ToLinear1(c.g), ToLinear1(c.b));
#else
	return c;
#endif
}

float ToSrgb1(float c)
{
	return (c < 0.0031308) ? c * 12.92 : 1.055 * pow(abs(c), 0.41666) - 0.055;
}

float3 ToSrgb(float3 c)
{
#if CRT_LINEAR_GAMMA
	return float3(ToSrgb1(c.r), ToSrgb1(c.g), ToSrgb1(c.b));
#else
	return c;
#endif
}

// Nearest emulated pixel, averaged over the source rows around its centre.
float3 Fetch(float2 pos, float2 off)
{
	pos = (floor(pos * CrtRes + off) + 0.5) / CrtRes;
	if (max(abs(pos.x - 0.5), abs(pos.y - 0.5)) > 0.5)
		return float3(0.0, 0.0, 0.0);
	const float2 rowOffset = float2(0.0, 0.5 * BUFFER_RCP_HEIGHT);
	float3 c = 0.5 * (tex2D(CrtBackBuffer, pos - rowOffset).rgb + tex2D(CrtBackBuffer, pos + rowOffset).rgb);
	return ToLinear(CRT_BRIGHT_BOOST * c);
}

float2 Dist(float2 pos)
{
	pos = pos * CrtRes;
	return -((pos - floor(pos)) - 0.5);
}

float Gaus(float pos, float scale)
{
	return exp2(scale * pow(abs(pos), CRT_SHAPE));
}

float3 Horz3(float2 pos, float off)
{
	float3 b = Fetch(pos, float2(-1.0, off));
	float3 c = Fetch(pos, float2(0.0, off));
	float3 d = Fetch(pos, float2(1.0, off));
	float dst = Dist(pos).x;
	float wb = Gaus(dst - 1.0, CRT_HARD_PIX);
	float wc = Gaus(dst + 0.0, CRT_HARD_PIX);
	float wd = Gaus(dst + 1.0, CRT_HARD_PIX);
	return (b * wb + c * wc + d * wd) / (wb + wc + wd);
}

float3 Horz5(float2 pos, float off)
{
	float3 a = Fetch(pos, float2(-2.0, off));
	float3 b = Fetch(pos, float2(-1.0, off));
	float3 c = Fetch(pos, float2(0.0, off));
	float3 d = Fetch(pos, float2(1.0, off));
	float3 e = Fetch(pos, float2(2.0, off));
	float dst = Dist(pos).x;
	float wa = Gaus(dst - 2.0, CRT_HARD_PIX);
	float wb = Gaus(dst - 1.0, CRT_HARD_PIX);
	float wc = Gaus(dst + 0.0, CRT_HARD_PIX);
	float wd = Gaus(dst + 1.0, CRT_HARD_PIX);
	float we = Gaus(dst + 2.0, CRT_HARD_PIX);
	return (a * wa + b * wb + c * wc + d * wd + e * we) / (wa + wb + wc + wd + we);
}

float Scan(float2 pos, float off)
{
	return Gaus(Dist(pos).y + off, CRT_HARD_SCAN);
}

float3 Tri(float2 pos)
{
	float3 a = Horz3(pos, -1.0);
	float3 b = Horz5(pos, 0.0);
	float3 c = Horz3(pos, 1.0);
	return a * Scan(pos, -1.0) + b * Scan(pos, 0.0) + c * Scan(pos, 1.0);
}

#if CRT_BLOOM
float3 Horz7(float2 pos, float off)
{
	float3 a = Fetch(pos, float2(-3.0, off));
	float3 b = Fetch(pos, float2(-2.0, off));
	float3 c = Fetch(pos, float2(-1.0, off));
	float3 d = Fetch(pos, float2(0.0, off));
	float3 e = Fetch(pos, float2(1.0, off));
	float3 f = Fetch(pos, float2(2.0, off));
	float3 g = Fetch(pos, float2(3.0, off));
	float dst = Dist(pos).x;
	float wa = Gaus(dst - 3.0, CRT_HARD_BLOOM_PIX);
	float wb = Gaus(dst - 2.0, CRT_HARD_BLOOM_PIX);
	float wc = Gaus(dst - 1.0, CRT_HARD_BLOOM_PIX);
	float wd = Gaus(dst + 0.0, CRT_HARD_BLOOM_PIX);
	float we = Gaus(dst + 1.0, CRT_HARD_BLOOM_PIX);
	float wf = Gaus(dst + 2.0, CRT_HARD_BLOOM_PIX);
	float wg = Gaus(dst + 3.0, CRT_HARD_BLOOM_PIX);
	return (a * wa + b * wb + c * wc + d * wd + e * we + f * wf + g * wg) / (wa + wb + wc + wd + we + wf + wg);
}

float BloomScan(float2 pos, float off)
{
	return Gaus(Dist(pos).y + off, CRT_HARD_BLOOM_SCAN);
}

float3 Bloom(float2 pos)
{
	float3 a = Horz5(pos, -2.0);
	float3 b = Horz7(pos, -1.0);
	float3 c = Horz7(pos, 0.0);
	float3 d = Horz7(pos, 1.0);
	float3 e = Horz5(pos, 2.0);
	return a * BloomScan(pos, -2.0) + b * BloomScan(pos, -1.0) + c * BloomScan(pos, 0.0)
		+ d * BloomScan(pos, 1.0) + e * BloomScan(pos, 2.0);
}
#endif

float2 Warp(float2 pos)
{
	pos = pos * 2.0 - 1.0;
	pos *= float2(1.0 + (pos.y * pos.y) * CrtWarp.x, 1.0 + (pos.x * pos.x) * CrtWarp.y);
	return pos * 0.5 + 0.5;
}

float3 Mask(float2 pos)
{
	float3 mask = float3(CRT_MASK_DARK, CRT_MASK_DARK, CRT_MASK_DARK);
#if CRT_SHADOW_MASK == 1
	// Very compressed TV style shadow mask.
	float scanLine = CRT_MASK_LIGHT;
	float odd = (frac(pos.x / 6.0) < 0.5) ? 1.0 : 0.0;
	if (frac((pos.y + odd) / 2.0) < 0.5)
		scanLine = CRT_MASK_DARK;
	pos.x = frac(pos.x / 3.0);
	if (pos.x < 0.333) mask.r = CRT_MASK_LIGHT;
	else if (pos.x < 0.666) mask.g = CRT_MASK_LIGHT;
	else mask.b = CRT_MASK_LIGHT;
	mask *= scanLine;
#elif CRT_SHADOW_MASK == 2
	// Aperture grille.
	pos.x = frac(pos.x / 3.0);
	if (pos.x < 0.333) mask.r = CRT_MASK_LIGHT;
	else if (pos.x < 0.666) mask.g = CRT_MASK_LIGHT;
	else mask.b = CRT_MASK_LIGHT;
#elif CRT_SHADOW_MASK == 3
	// Stretched VGA style shadow mask.
	pos.x += pos.y * 3.0;
	pos.x = frac(pos.x / 6.0);
	if (pos.x < 0.333) mask.r = CRT_MASK_LIGHT;
	else if (pos.x < 0.666) mask.g = CRT_MASK_LIGHT;
	else mask.b = CRT_MASK_LIGHT;
#elif CRT_SHADOW_MASK == 4
	// VGA style shadow mask.
	pos.xy = floor(pos.xy * float2(1.0, 0.5));
	pos.x += pos.y * 3.0;
	pos.x = frac(pos.x / 6.0);
	if (pos.x < 0.333) mask.r = CRT_MASK_LIGHT;
	else if (pos.x < 0.666) mask.g = CRT_MASK_LIGHT;
	else mask.b = CRT_MASK_LIGHT;
#else
	mask = float3(1.0, 1.0, 1.0);
#endif
	return mask;
}

float4 CrtLottesPS(float4 vpos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
	float2 pos = Warp(texcoord);
	float3 color = Tri(pos);
#if CRT_BLOOM
	color += Bloom(pos) * CRT_BLOOM_AMOUNT;
#endif
	color *= Mask(floor(vpos.xy) + 0.5);
	return float4(ToSrgb(color), 1.0);
}

technique CrtLottes
{
	pass CrtLottesPass
	{
		VertexShader = CrtFullscreenVS;
		PixelShader = CrtLottesPS;
	}
}
