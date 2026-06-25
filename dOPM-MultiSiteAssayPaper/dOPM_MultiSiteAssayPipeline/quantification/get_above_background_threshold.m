function t = get_above_background_threshold(z,overpeak_ratio)

   z = z(z~=0);
   minval = quantile(z(:),0.0001); % safer..
    
   [cnt,vls] = histcounts(z(:),1:max(z(:)));
   maxpeakval = find(cnt==max(cnt));
   maxpeakval = maxpeakval(1);
   %
   t = vls(maxpeakval) + overpeak_ratio*(vls(maxpeakval)-minval);
   
end