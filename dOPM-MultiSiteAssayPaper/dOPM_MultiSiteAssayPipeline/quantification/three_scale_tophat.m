function z = three_scale_tophat(U,S1,S2,S3,a1)
    U1 = gauss3filter(U,S1);
    U2 = gauss3filter(U,S2);
    U3 = gauss3filter(U,S3);                               
    %
    u1 = (U1-U2)./U2;
    u2 = (U2-U3)./U3;
    %
    z = u1*a1 + u2*(1-a1);  
end