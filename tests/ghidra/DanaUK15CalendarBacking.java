// @category Dana
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;
import java.io.*;
import java.util.*;
public class DanaUK15CalendarBacking extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(new FileWriter(getScriptArgs()[0]));
  byte[] data=new byte[0x5d0000];currentProgram.getMemory().getBytes(toAddr(0x10000000),data);
  long table=0;
  for(int i=0;i<data.length-4;i+=2){
   long v=((long)(data[i]&255)<<24)|((data[i+1]&255)<<16)|((data[i+2]&255)<<8)|(data[i+3]&255);
   if(v==0x1007fdc2L){
    long base=0x10000000L+i-0xf5*4;
    out.printf("TIM_GET_POINTER %08X CANDIDATE_TABLE %08X NEXT %08X\n",0x10000000L+i,base,getInt(toAddr(base+0xf6*4)));
    table=base;
   }
  }
  LinkedHashSet<Long> starts=new LinkedHashSet<>(Arrays.asList(0x1007fceeL,0x1007fdc2L,0x1007fe0aL,0x1008004eL,0x10016668L,0x10042296L,0x100421faL,0x1001a27aL,0x10015c62L,0x103275c0L));
  if(table!=0)for(int n:new int[]{0x3f,0xf5,0xf6,0xfc,0xfd}){
   long v=Integer.toUnsignedLong(getInt(toAddr(table+4*n)));out.printf("TRAP A%03X TARGET %08X\n",n,v);if(v>=0x10000000L && v<0x105d0000L)starts.add(v);
  }
  DecompInterface d=new DecompInterface();d.openProgram(currentProgram);
  for(long start:starts){
   out.printf("FUNCTION %08X\n",start);
   clearListing(toAddr(start),toAddr(start+0x300));
   disassemble(toAddr(start));
   long pc=start;int returns=0;
   for(int k=0;k<150;k++){
    Instruction ins=getInstructionAt(toAddr(pc));if(ins==null){disassemble(toAddr(pc));ins=getInstructionAt(toAddr(pc));}
    if(ins==null){out.printf("%08X ??\n",pc);break;}
    out.printf("%08X %s",pc,ins);
    boolean trap=ins.getMnemonicString().equalsIgnoreCase("trap");
    if(trap){out.printf(" PALM_TRAP=%04X",getShort(toAddr(pc+2))&65535);ins.setFallThrough(toAddr(pc+4));}
    out.println();
    pc+=ins.getLength();if(trap)pc+=2;
    if(ins.getMnemonicString().equalsIgnoreCase("rts")){returns++;if(returns>=1)break;}
   }
   Function f=getFunctionAt(toAddr(start));if(f==null)try{f=createFunction(toAddr(start),null);}catch(Exception e){}
   if(f!=null){DecompileResults result=d.decompileFunction(f,25,monitor);if(result.decompileCompleted())out.println(result.getDecompiledFunction().getC());else out.println(result.getErrorMessage());}
  }
  d.dispose();out.close();
 }
}