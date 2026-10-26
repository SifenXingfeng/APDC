Includes = {
}

PixelShader =
{
	Samplers =
	{
		TextureOne =
		{
			Index = 0
			MagFilter = "Linear"
			MinFilter = "Linear"
			MipFilter = "None"
			AddressU = "Wrap"
			AddressV = "Wrap"
		}
		TextureTwo =
		{
			Index = 1
			MagFilter = "Point"
			MinFilter = "Point"
			MipFilter = "None"
			AddressU = "Wrap"
			AddressV = "Wrap"
		}
	}
}


VertexStruct VS_INPUT
{
	float4 vPosition  : POSITION;
	float2 vTexCoord  : TEXCOORD0;
};

VertexStruct VS_OUTPUT
{
	float4  vPosition : PDX_POSITION;
	float2  vTexCoord0 : TEXCOORD0;
};


ConstantBuffer( 0, 0 )
{
	float4x4 WorldViewProjectionMatrix; 
	float4 vFirstColor;
	float4 vSecondColor;
	float CurrentState;
};


VertexShader =
{
	MainCode VertexShader
	[[
		
		VS_OUTPUT main(const VS_INPUT v )
		{
			VS_OUTPUT Out;
		   	Out.vPosition  = mul( WorldViewProjectionMatrix, v.vPosition );
			Out.vTexCoord0  = v.vTexCoord;
			Out.vTexCoord0.y = -Out.vTexCoord0.y;
		
			return Out;
		}
		
	]]
}

PixelShader =
{
	MainCode PixelColor
	[[
		
		float4 main( VS_OUTPUT v ) : PDX_COLOR
		{
			if( v.vTexCoord0.x <= CurrentState )
				return vFirstColor;
			else
				return vSecondColor;
		}
		
	]]

	MainCode PixelTexture
	[[
		
		float4 main( VS_OUTPUT v ) : PDX_COLOR
		{
            float4 mask = tex2D(TextureOne, v.vTexCoord0.xy);
            float packed = floor(CurrentState * 12273.f + 0.5f)-1.f;
            float z = floor(packed / 472.f);
            float paletteSlot = packed - z*472.f;
            float zoom = exp2(-4.f + z*0.5f);
            float4 fill = tex2D(TextureTwo, float2((paletteSlot+0.5f)/472.f,0.5f));
            float distance = (mask.r*255.f-127.5f)*0.5f;
            float alpha = smoothstep(-0.5f,0.5f,distance*zoom);
            float edge = mask.b*127.5f*zoom;
            float fine = 1.f-smoothstep(0.5f,1.1f,mask.g*127.5f*zoom);
            float3 col = lerp(fill.rgb,float3(0.54f,0.72f,0.86f),fine*0.8f);
            if (vFirstColor.r>0.5f) { edge=mask.r*127.5f*zoom; alpha=0.f; col=float3(0.55f,0.75f,0.94f); }
            float halo=1.f-smoothstep(1.f,2.f,edge);
            float core=1.f-smoothstep(0.4f,1.1f,edge);
            col=lerp(col,float3(0.55f,0.75f,0.94f),halo);
            col=lerp(col,float3(0.89f,0.96f,1.f),core);
            alpha=max(alpha,halo);
            return float4(col,alpha);
		}

	]]
}


BlendState BlendState
{
	BlendEnable = yes
	SourceBlend = "SRC_ALPHA"
	DestBlend = "INV_SRC_ALPHA"
}


Effect Color
{
	VertexShader = "VertexShader"
	PixelShader = "PixelColor"
}

Effect Texture
{
	VertexShader = "VertexShader"
	PixelShader = "PixelTexture"
}
