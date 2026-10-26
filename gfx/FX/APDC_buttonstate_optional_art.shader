# Available law artwork; disabled input leaves the status icons visible.
Includes = {
	"buttonstate.fxh"
}

PixelShader =
{
	Samplers =
	{
		MapTexture =
		{
			Index = 0
			MagFilter = "Linear"
			MinFilter = "Linear"
			MipFilter = "None"
			AddressU = "Clamp"
			AddressV = "Clamp"
			MipMapLodBias = -0.8
		}
	}
}

VertexStruct VS_OUTPUT
{
	float4 vPosition : PDX_POSITION;
	float2 vTexCoord : TEXCOORD0;
};

VertexShader =
{
	MainCode VertexShader
	[[
		VS_OUTPUT main(const VS_INPUT v)
		{
			VS_OUTPUT Out;
			Out.vPosition = mul(WorldViewProjectionMatrix, float4(v.vPosition.xyz, 1));
			Out.vTexCoord = v.vTexCoord;
			Out.vTexCoord += Offset;
			return Out;
		}
	]]
}

PixelShader =
{
	MainCode PixelShaderUp
	[[
		float4 main(VS_OUTPUT v) : PDX_COLOR
		{
			float4 OutColor = tex2D(MapTexture, v.vTexCoord);
			OutColor *= Color;
			return OutColor;
		}
	]]

	MainCode PixelShaderDown
	[[
		float4 main(VS_OUTPUT v) : PDX_COLOR
		{
			float4 OutColor = tex2D(MapTexture, v.vTexCoord);
			OutColor *= Color;

			float vTime = 0.9 - saturate((Time - AnimationTime) * 16);
			vTime *= vTime;
			vTime = 0.9 * 0.9 - vTime;
			float4 MixColor = float4(0.15, 0.15, 0.15, 0) * vTime;
			OutColor.rgb -= (0.5 + OutColor.rgb) * MixColor.rgb;

			return OutColor;
		}
	]]

	MainCode PixelShaderDisable
	[[
        float4 main(VS_OUTPUT v) : PDX_COLOR
        {
            // The selected/locked artwork is provided by the existing icons.
            return float4(0, 0, 0, 0);
        }
    ]]

	MainCode PixelShaderOver
	[[
		float4 main(VS_OUTPUT v) : PDX_COLOR
		{
			float4 OutColor = tex2D(MapTexture, v.vTexCoord);
			OutColor *= Color;

			float vTime = 0.9 - saturate((Time - AnimationTime) * 4);
			vTime *= vTime;
			vTime = 0.9 * 0.9 - vTime;
			float4 MixColor = float4(0.15, 0.15, 0.15, 0) * vTime;
			OutColor.rgb += (0.5 + OutColor.rgb) * MixColor.rgb;

			return OutColor;
		}
	]]
}

BlendState BlendState
{
	BlendEnable = yes
	SourceBlend = "src_alpha"
	DestBlend = "inv_src_alpha"
}

Effect Up
{
	VertexShader = "VertexShader"
	PixelShader = "PixelShaderUp"
}

Effect Down
{
	VertexShader = "VertexShader"
	PixelShader = "PixelShaderDown"
}

Effect Disable
{
	VertexShader = "VertexShader"
	PixelShader = "PixelShaderDisable"
}

Effect Over
{
	VertexShader = "VertexShader"
	PixelShader = "PixelShaderOver"
}
